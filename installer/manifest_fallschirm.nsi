!cd "${__FILEDIR__}"
!cd ..

Unicode True

Name "manifest_fallschirm"
OutFile "dist\manifest_fallschirm-setup.exe"
InstallDir "$PROGRAMFILES\manifest_fallschirm"
RequestExecutionLevel admin

Page directory
Page instfiles

Section "Install"
  SetOutPath "$INSTDIR"
  File "README.md"

  WriteUninstaller "$INSTDIR\uninstall.exe"

  CreateDirectory "$SMPROGRAMS\manifest_fallschirm"
  CreateShortcut "$SMPROGRAMS\manifest_fallschirm\Uninstall manifest_fallschirm.lnk" "$INSTDIR\uninstall.exe"
SectionEnd

Section "Uninstall"
  Delete "$SMPROGRAMS\manifest_fallschirm\Uninstall manifest_fallschirm.lnk"
  RMDir "$SMPROGRAMS\manifest_fallschirm"
  Delete "$INSTDIR\README.md"
  Delete "$INSTDIR\uninstall.exe"
  RMDir "$INSTDIR"
SectionEnd
