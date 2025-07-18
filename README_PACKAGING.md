# 松瓷机电AI助手程序打包说明

本文档介绍如何使用`build_exe.py`脚本将松瓷机电AI助手程序打包为可执行文件和安装程序。

## 打包工具介绍

`build_exe.py`是一个用于将松瓷机电AI助手打包为可执行文件和安装程序的Python脚本。它使用PyInstaller处理打包过程，并可选地使用NSIS创建安装程序。

## 前置条件

在使用打包脚本前，请确保以下条件已满足：

1. 已安装Python 3.8或更高版本
2. 已安装PyInstaller：`pip install pyinstaller`
3. 已安装松瓷机电AI助手程序所需的所有依赖（脚本会自动检查并提示安装）
4. （可选）如需创建安装程序，请安装NSIS：[https://nsis.sourceforge.io/Download](https://nsis.sourceforge.io/Download)

## 打包步骤

1. 将`build_exe.py`脚本放在松瓷机电AI助手程序的根目录
2. 打开命令行，导航到该目录
3. 运行脚本：`python build_exe.py`
4. 按照脚本的指示进行操作

## 打包过程说明

脚本执行期间会进行以下操作：

1. **检查依赖**：检查必要的Python包是否已安装，如未安装会提示安装。
2. **创建应用信息**：生成包含应用名称、版本等信息的JSON文件。
3. **准备文件**：创建临时目录，生成版本信息文件，确保图标文件存在。
4. **创建规格文件**：生成PyInstaller的spec文件，定义要包含的文件和目录。
5. **构建可执行文件**：使用PyInstaller构建独立的可执行文件。
6. **创建安装程序**（可选）：如果已安装NSIS，使用NSIS创建安装程序。
7. **清理临时文件**：删除打包过程中生成的临时文件。

## 配置选项

打包过程中，脚本会询问一些配置选项：

- **是否包含AI模型文件**：选择`y`将模型文件一同打包（会显著增加打包体积），选择`n`则不包含模型文件（应用将在首次运行时下载模型）。

## 输出文件

成功执行后，脚本会生成以下文件：

- **可执行文件**：位于`dist\松瓷机电AI助手\松瓷机电AI助手.exe`
- **安装程序**（如果已安装NSIS）：位于`dist\松瓷机电AI助手_Setup_1.0.0.exe`

## 常见问题

### 打包过程中出现错误

- **依赖错误**：确保所有必要的Python包都已正确安装。
- **文件路径错误**：确保脚本放置在正确的目录中，且与松瓷机电AI助手程序的主文件位于同一目录。
- **权限错误**：尝试使用管理员权限运行命令行。

### 打包后程序无法运行

- **缺少DLL**：可能是某些依赖项未正确打包，尝试添加相关的隐藏导入。
- **模型加载错误**：检查模型路径是否正确，或尝试将模型文件手动复制到输出目录。

### 生成的安装程序无法安装

- **NSIS错误**：确保NSIS已正确安装，且路径已添加到环境变量中。
- **文件冲突**：确保目标安装路径没有与现有文件冲突。

## 自定义打包

如需自定义打包过程，可编辑`build_exe.py`文件的以下部分：

- **依赖列表**：修改`check_dependencies`函数中的`required_packages`列表。
- **应用信息**：修改`create_app_info`函数中的应用信息字典。
- **包含的文件**：修改`create_spec_file`函数中的`directories_to_include`和`extra_files`列表。
- **NSIS脚本**：修改`create_installer`函数中的NSIS脚本内容。

## 注意事项

- 打包过程可能需要较长时间，尤其是包含大型模型文件时。
- 打包生成的可执行文件体积可能较大，取决于所包含的依赖和模型文件。
- 某些杀毒软件可能会将PyInstaller打包的程序误报为恶意软件，这是误报。 