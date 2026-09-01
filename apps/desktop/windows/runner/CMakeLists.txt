cmake_minimum_required(VERSION 3.14)
project(runner LANGUAGES CXX)

set(ILAIOS_CANONICAL_APP_ICON "${CMAKE_CURRENT_SOURCE_DIR}/../../../../brand/assets/05-ilaios-app-icon.jpg")
set(ILAIOS_WINDOWS_APP_ICON "${CMAKE_CURRENT_SOURCE_DIR}/resources/app_icon.ico")
set(ILAIOS_ICON_GENERATOR "${CMAKE_CURRENT_SOURCE_DIR}/../../tool/generate_windows_icon.ps1")

add_custom_command(
  OUTPUT "${ILAIOS_WINDOWS_APP_ICON}"
  COMMAND powershell.exe -NoProfile -ExecutionPolicy Bypass -File "${ILAIOS_ICON_GENERATOR}"
          -SourceJpeg "${ILAIOS_CANONICAL_APP_ICON}"
          -OutputIco "${ILAIOS_WINDOWS_APP_ICON}"
  DEPENDS "${ILAIOS_CANONICAL_APP_ICON}" "${ILAIOS_ICON_GENERATOR}"
  COMMENT "Deriving Windows app icon from canonical ILAIOS app-icon master"
  VERBATIM
)
add_custom_target(ilaios_brand_icon DEPENDS "${ILAIOS_WINDOWS_APP_ICON}")

# Define the application target. To change its name, change BINARY_NAME in the
# top-level CMakeLists.txt, not the value here, or `flutter run` will no longer
# work.
#
# Any new source files that you add to the application should be added here.
add_executable(${BINARY_NAME} WIN32
  "flutter_window.cpp"
  "main.cpp"
  "utils.cpp"
  "win32_window.cpp"
  "${FLUTTER_MANAGED_DIR}/generated_plugin_registrant.cc"
  "Runner.rc"
  "runner.exe.manifest"
)

# Apply the standard set of build settings. This can be removed for applications
# that need different build settings.
apply_standard_settings(${BINARY_NAME})

# Add preprocessor definitions for the build version.
target_compile_definitions(${BINARY_NAME} PRIVATE "FLUTTER_VERSION=\"${FLUTTER_VERSION}\"")
target_compile_definitions(${BINARY_NAME} PRIVATE "FLUTTER_VERSION_MAJOR=${FLUTTER_VERSION_MAJOR}")
target_compile_definitions(${BINARY_NAME} PRIVATE "FLUTTER_VERSION_MINOR=${FLUTTER_VERSION_MINOR}")
target_compile_definitions(${BINARY_NAME} PRIVATE "FLUTTER_VERSION_PATCH=${FLUTTER_VERSION_PATCH}")
target_compile_definitions(${BINARY_NAME} PRIVATE "FLUTTER_VERSION_BUILD=${FLUTTER_VERSION_BUILD}")

# Disable Windows macros that collide with C++ standard library functions.
target_compile_definitions(${BINARY_NAME} PRIVATE "NOMINMAX")

# Add dependency libraries and include directories. Add any application-specific
# dependencies here.
target_link_libraries(${BINARY_NAME} PRIVATE flutter flutter_wrapper_app)
target_link_libraries(${BINARY_NAME} PRIVATE "dwmapi.lib" "shell32.lib")
target_include_directories(${BINARY_NAME} PRIVATE "${CMAKE_SOURCE_DIR}")

# Run the Flutter tool portions of the build. This must not be removed.
add_dependencies(${BINARY_NAME} flutter_assemble ilaios_brand_icon)
