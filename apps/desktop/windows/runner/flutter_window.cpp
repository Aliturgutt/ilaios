#include "flutter_window.h"

#include <shellapi.h>
#include <shobjidl.h>

#include <iterator>
#include <optional>
#include <string>
#include <utility>
#include <vector>

#include "flutter/generated_plugin_registrant.h"
#include "utils.h"

namespace {

constexpr char kReferenceAssetChannel[] = "ilaios/reference_assets";
constexpr char kPickImagesMethod[] = "pickImages";
constexpr char kFilesDroppedMethod[] = "filesDropped";

flutter::EncodableList PickReferenceImages(HWND owner) {
  flutter::EncodableList output;
  IFileOpenDialog* dialog = nullptr;
  HRESULT result = CoCreateInstance(CLSID_FileOpenDialog, nullptr,
                                    CLSCTX_INPROC_SERVER, IID_PPV_ARGS(&dialog));
  if (FAILED(result) || dialog == nullptr) {
    return output;
  }

  DWORD options = 0;
  if (SUCCEEDED(dialog->GetOptions(&options))) {
    dialog->SetOptions(options | FOS_ALLOWMULTISELECT | FOS_FILEMUSTEXIST |
                       FOS_PATHMUSTEXIST | FOS_FORCEFILESYSTEM);
  }
  const COMDLG_FILTERSPEC filters[] = {
      {L"Reference images", L"*.png;*.jpg;*.jpeg;*.webp"},
      {L"PNG images", L"*.png"},
      {L"JPEG images", L"*.jpg;*.jpeg"},
      {L"WebP images", L"*.webp"},
  };
  dialog->SetFileTypes(static_cast<UINT>(std::size(filters)), filters);
  dialog->SetFileTypeIndex(1);
  dialog->SetTitle(L"Select Web / Video reference images");

  result = dialog->Show(owner);
  if (SUCCEEDED(result)) {
    IShellItemArray* items = nullptr;
    if (SUCCEEDED(dialog->GetResults(&items)) && items != nullptr) {
      DWORD count = 0;
      if (SUCCEEDED(items->GetCount(&count))) {
        for (DWORD index = 0; index < count; ++index) {
          IShellItem* item = nullptr;
          if (FAILED(items->GetItemAt(index, &item)) || item == nullptr) {
            continue;
          }
          PWSTR wide_path = nullptr;
          if (SUCCEEDED(item->GetDisplayName(SIGDN_FILESYSPATH, &wide_path)) &&
              wide_path != nullptr) {
            std::string path = Utf8FromUtf16(wide_path);
            if (!path.empty()) {
              output.emplace_back(path);
            }
            CoTaskMemFree(wide_path);
          }
          item->Release();
        }
      }
      items->Release();
    }
  }
  dialog->Release();
  return output;
}

flutter::EncodableList DroppedFilePaths(HDROP drop) {
  flutter::EncodableList paths;
  const UINT count = DragQueryFileW(drop, 0xFFFFFFFF, nullptr, 0);
  for (UINT index = 0; index < count; ++index) {
    const UINT length = DragQueryFileW(drop, index, nullptr, 0);
    if (length == 0) {
      continue;
    }
    std::wstring wide_path(length + 1, L'\0');
    if (DragQueryFileW(drop, index, wide_path.data(), length + 1) == 0) {
      continue;
    }
    wide_path.resize(length);
    std::string path = Utf8FromUtf16(wide_path.c_str());
    if (!path.empty()) {
      paths.emplace_back(path);
    }
  }
  return paths;
}

}  // namespace

FlutterWindow::FlutterWindow(const flutter::DartProject& project)
    : project_(project) {}

FlutterWindow::~FlutterWindow() {}

bool FlutterWindow::OnCreate() {
  if (!Win32Window::OnCreate()) {
    return false;
  }

  RECT frame = GetClientArea();
  flutter_controller_ = std::make_unique<flutter::FlutterViewController>(
      frame.right - frame.left, frame.bottom - frame.top, project_);
  if (!flutter_controller_->engine() || !flutter_controller_->view()) {
    return false;
  }
  RegisterPlugins(flutter_controller_->engine());
  SetChildContent(flutter_controller_->view()->GetNativeWindow());

  reference_asset_channel_ =
      std::make_unique<flutter::MethodChannel<flutter::EncodableValue>>(
          flutter_controller_->engine()->messenger(), kReferenceAssetChannel,
          &flutter::StandardMethodCodec::GetInstance());
  reference_asset_channel_->SetMethodCallHandler(
      [this](const flutter::MethodCall<flutter::EncodableValue>& call,
             std::unique_ptr<flutter::MethodResult<flutter::EncodableValue>>
                 result) {
        if (call.method_name() == kPickImagesMethod) {
          result->Success(flutter::EncodableValue(PickReferenceImages(GetHandle())));
          return;
        }
        result->NotImplemented();
      });

  // Flutter's child HWND covers the client area, so register the child itself
  // for WM_DROPFILES and preserve its original window procedure. This avoids
  // a false "drop enabled" state where the parent is registered but never
  // receives drops over the Flutter surface.
  flutter_child_window_ = flutter_controller_->view()->GetNativeWindow();
  if (!SetPropW(flutter_child_window_, L"ILAIOS_REFERENCE_DROP_OWNER", this)) {
    return false;
  }
  SetLastError(0);
  original_flutter_child_proc_ = reinterpret_cast<WNDPROC>(SetWindowLongPtrW(
      flutter_child_window_, GWLP_WNDPROC,
      reinterpret_cast<LONG_PTR>(&FlutterWindow::FlutterChildWindowProc)));
  if (original_flutter_child_proc_ == nullptr && GetLastError() != 0) {
    RemovePropW(flutter_child_window_, L"ILAIOS_REFERENCE_DROP_OWNER");
    return false;
  }
  DragAcceptFiles(flutter_child_window_, TRUE);

  flutter_controller_->engine()->SetNextFrameCallback([&]() { this->Show(); });
  flutter_controller_->ForceRedraw();
  return true;
}

void FlutterWindow::OnDestroy() {
  if (flutter_child_window_ != nullptr) {
    DragAcceptFiles(flutter_child_window_, FALSE);
    RemovePropW(flutter_child_window_, L"ILAIOS_REFERENCE_DROP_OWNER");
    if (original_flutter_child_proc_ != nullptr) {
      SetWindowLongPtrW(flutter_child_window_, GWLP_WNDPROC,
                        reinterpret_cast<LONG_PTR>(original_flutter_child_proc_));
    }
  }
  flutter_child_window_ = nullptr;
  original_flutter_child_proc_ = nullptr;
  reference_asset_channel_.reset();
  if (flutter_controller_) {
    flutter_controller_ = nullptr;
  }
  Win32Window::OnDestroy();
}

LRESULT FlutterWindow::MessageHandler(HWND hwnd, UINT const message,
                                      WPARAM const wparam,
                                      LPARAM const lparam) noexcept {
  if (message == WM_DROPFILES) {
    HandleDroppedFiles(reinterpret_cast<HDROP>(wparam));
    return 0;
  }

  if (flutter_controller_) {
    std::optional<LRESULT> result =
        flutter_controller_->HandleTopLevelWindowProc(hwnd, message, wparam,
                                                      lparam);
    if (result) {
      return *result;
    }
  }

  switch (message) {
    case WM_FONTCHANGE:
      if (flutter_controller_) {
        flutter_controller_->engine()->ReloadSystemFonts();
      }
      break;
  }

  return Win32Window::MessageHandler(hwnd, message, wparam, lparam);
}

LRESULT CALLBACK FlutterWindow::FlutterChildWindowProc(
    HWND window, UINT message, WPARAM wparam, LPARAM lparam) noexcept {
  auto* owner = reinterpret_cast<FlutterWindow*>(
      GetPropW(window, L"ILAIOS_REFERENCE_DROP_OWNER"));
  if (owner != nullptr && message == WM_DROPFILES) {
    owner->HandleDroppedFiles(reinterpret_cast<HDROP>(wparam));
    return 0;
  }
  if (owner != nullptr && owner->original_flutter_child_proc_ != nullptr) {
    return CallWindowProcW(owner->original_flutter_child_proc_, window, message,
                           wparam, lparam);
  }
  return DefWindowProcW(window, message, wparam, lparam);
}

void FlutterWindow::HandleDroppedFiles(HDROP drop) {
  flutter::EncodableList paths = DroppedFilePaths(drop);
  DragFinish(drop);
  if (reference_asset_channel_ && !paths.empty()) {
    reference_asset_channel_->InvokeMethod(
        kFilesDroppedMethod,
        std::make_unique<flutter::EncodableValue>(std::move(paths)));
  }
}
