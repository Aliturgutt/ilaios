#include "flutter_window.h"

#include <optional>
#include <string>
#include <utility>

#include "flutter/generated_plugin_registrant.h"
#include "utils.h"

namespace {

constexpr char kReferenceDropChannel[] = "ilaios/reference-assets-drop";
constexpr char kDroppedPathsMethod[] = "droppedPaths";
constexpr wchar_t kDropOwnerProperty[] = L"ILAIOS_REFERENCE_DROP_OWNER";

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

  reference_drop_channel_ =
      std::make_unique<flutter::MethodChannel<flutter::EncodableValue>>(
          flutter_controller_->engine()->messenger(), kReferenceDropChannel,
          &flutter::StandardMethodCodec::GetInstance());

  // The Flutter child HWND covers the complete client area. Register and
  // subclass that HWND itself; registering only the top-level parent creates a
  // false-positive drop configuration because drops land on the child surface.
  flutter_child_window_ = flutter_controller_->view()->GetNativeWindow();
  if (!SetPropW(flutter_child_window_, kDropOwnerProperty, this)) {
    return false;
  }
  SetLastError(0);
  original_flutter_child_proc_ = reinterpret_cast<WNDPROC>(SetWindowLongPtrW(
      flutter_child_window_, GWLP_WNDPROC,
      reinterpret_cast<LONG_PTR>(&FlutterWindow::FlutterChildWindowProc)));
  if (original_flutter_child_proc_ == nullptr && GetLastError() != 0) {
    RemovePropW(flutter_child_window_, kDropOwnerProperty);
    flutter_child_window_ = nullptr;
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
    RemovePropW(flutter_child_window_, kDropOwnerProperty);
    if (original_flutter_child_proc_ != nullptr) {
      SetWindowLongPtrW(flutter_child_window_, GWLP_WNDPROC,
                        reinterpret_cast<LONG_PTR>(original_flutter_child_proc_));
    }
  }
  flutter_child_window_ = nullptr;
  original_flutter_child_proc_ = nullptr;
  reference_drop_channel_.reset();
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
      GetPropW(window, kDropOwnerProperty));
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
  if (reference_drop_channel_ && !paths.empty()) {
    reference_drop_channel_->InvokeMethod(
        kDroppedPathsMethod,
        std::make_unique<flutter::EncodableValue>(std::move(paths)));
  }
}
