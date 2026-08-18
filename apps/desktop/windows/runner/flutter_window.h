#ifndef RUNNER_FLUTTER_WINDOW_H_
#define RUNNER_FLUTTER_WINDOW_H_

#include "win32_window.h"

#include <shellapi.h>

#include <flutter/dart_project.h>
#include <flutter/flutter_view_controller.h>
#include <flutter/method_channel.h>
#include <flutter/standard_method_codec.h>

#include <memory>

// Hosts the Flutter view plus the native Windows reference-image drop boundary.
// Only local file paths cross this channel; Dart and the authenticated backend
// keep responsibility for content validation, ownership and request binding.
class FlutterWindow : public Win32Window {
 public:
  explicit FlutterWindow(const flutter::DartProject& project);
  virtual ~FlutterWindow();

 protected:
  bool OnCreate() override;
  void OnDestroy() override;
  LRESULT MessageHandler(HWND window, UINT const message, WPARAM const wparam,
                         LPARAM const lparam) noexcept override;

 private:
  static LRESULT CALLBACK FlutterChildWindowProc(HWND window, UINT message,
                                                  WPARAM wparam,
                                                  LPARAM lparam) noexcept;
  void HandleDroppedFiles(HDROP drop);

  flutter::DartProject project_;
  std::unique_ptr<flutter::FlutterViewController> flutter_controller_;
  std::unique_ptr<flutter::MethodChannel<flutter::EncodableValue>>
      reference_drop_channel_;
  HWND flutter_child_window_ = nullptr;
  WNDPROC original_flutter_child_proc_ = nullptr;
};

#endif  // RUNNER_FLUTTER_WINDOW_H_
