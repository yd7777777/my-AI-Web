@echo off
:: 设置窗口标题
title AI Streamlit Start
:: 切换到 UTF-8 编码防止中文乱码
chcp 65001 > nul
:: 切换到当前批处理文件所在的目录
cd /d "%~dp0"

echo 正在通过 Streamlit 启动 AI Web 界面...
echo ---------------------------------------

:: 使用 py -m 调用 streamlit 运行当前目录下的文件
py -m streamlit run AI_web.py

:: 如果运行失败，保留窗口查看报错信息
if %errorlevel% neq 0 (
    echo.
    echo [错误] 启动失败。请检查是否已安装 streamlit (pip install streamlit)。
)
pause