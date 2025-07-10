# PMAS - 专利侵权分析平台

PMAS (Patent Infringement Analysis System) 是一个旨在利用大型语言模型（LLM）和AI技术，分析专利文档并从提供的线索文件中挖掘潜在专利侵权风险的平台。

## 1. 项目背景与目标

（参考用户提供的项目介绍）

本项目旨在解决专利开发和知识产权管理中的痛点，例如权利要求识别困难、侵权判别复杂、维护成本高等问题。通过AI技术，平台期望实现：

*   **专利侵权线索挖掘**：自动化分析专利和潜在侵权证据。
*   **文本提取与处理**：支持多种文件格式（PDF, DOCX, Markdown, TXT）的文本内容提取，包括对PDF的OCR处理。
*   **LLM驱动的分析**：利用大模型的理解和推理能力进行技术特征对比和侵权风险评估。
*   **报告生成**：自动生成结构化的侵权分析报告。

## 2. 功能特性

*   **用户友好的Web界面**：
    *   上传核心专利文件（单个文件：PDF, DOCX, MD, TXT）或通过URL导入。
    *   上传侵权线索文件（单个、多个或ZIP压缩包，包含PDF, DOCX, MD, TXT文件）。
    *   实时（模拟）分析进度展示。
    *   在线查看Markdown格式的分析报告。
    *   下载Markdown或PDF格式的报告。
*   **后端处理流程**：
    *   **文件管理**：安全处理用户上传的文件，会话隔离。
    *   **文本提取**：
        *   PDF: PyPDF2 (基础), pdfplumber (高级, OCR准备)。未来可集成OCR。
        *   DOCX: python-docx。
        *   Markdown: Markdown库。
        *   TXT: 标准库。
    *   **侵权分析**：
        *   (当前为模拟) 通过LLM API（如OpenAI GPT, DeepSeek等）进行核心专利特征提取。
        *   (当前为模拟) 对比专利特征与侵权线索文件内容，评估匹配度与风险。
    *   **报告生成**：将分析结果格式化为Markdown报告。
*   **可配置性**：
    *   `config/settings.py`：配置API密钥、文件上传参数、LLM模型等。
    *   `config/evaluation_rules.yaml`：(未来可用于指导LLM或后处理) 侵权评估的参考标准。
    *   `prompts/prompt_templates.py`：(未来可用于实际LLM调用) 管理与LLM交互的提示。

## 3. 技术栈

*   **后端**：Python, Flask
*   **前端**：HTML, CSS, JavaScript, Bootstrap
*   **文件处理**：PyPDF2, python-docx, Markdown, pdfplumber, (pytesseract + Tesseract OCR for future OCR)
*   **PDF报告生成**：WeasyPrint (可选)
*   **LLM集成**：OpenAI API (或可替换为其他，如DeepSeek)

## 4. 快速入门

### 4.1 环境准备

1.  **Python版本**：Python 3.8+
2.  **克隆仓库**：
    ```bash
    git clone <repository_url>
    cd pmas-project
    ```
3.  **创建虚拟环境** (推荐):
    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/macOS
    # venv\Scripts\activate    # Windows
    ```
4.  **安装依赖包**：
    ```bash
    pip install -r requirements.txt
    ```
    *注意*: `pytesseract` 需要系统安装 Tesseract OCR 引擎。`WeasyPrint` 可能需要安装额外的系统库 (如 Pango, Cairo)。请参考其官方文档。

### 4.2 配置项目

1.  **复制配置文件模板** (如果它们不存在或在`.gitignore`中):
    *   `cp config/settings.py.example config/settings.py` (假设有example文件)
2.  **编辑 `config/settings.py`**：
    *   `OPENAI_API_KEY`: 填入您的LLM API密钥 (例如 OpenAI 或 DeepSeek 的密钥)。
    *   `SERP_API_KEY`: (如果使用) 填入您的搜索引擎API密钥。
    *   `SIMULATE_LLM`: 设置为 `False` 以尝试连接真实LLM API，或 `True` (默认) 以使用模拟数据和流程。
    *   `TESSERACT_CMD`: (如果使用OCR) 根据您的Tesseract安装路径配置。

### 4.3 运行应用

```bash
python app.py
```
应用默认运行在 `http://127.0.0.1:5001` (或 `app.py` 中指定的端口)。

### 4.4 使用步骤

1.  打开浏览器访问应用主页。
2.  **上传核心专利**：通过文件上传或URL输入方式提供您的专利文件。
3.  **上传侵权线索**：上传一个或多个线索文件，或一个包含这些文件的ZIP包。
4.  点击“**提交分析**”。
5.  系统将显示“**分析中**”页面，并（模拟）展示处理进度。
6.  分析完成后，自动跳转到“**报告页面**”，展示Markdown格式的分析报告。
7.  您可以选择下载Markdown或PDF格式的报告。

## 5. 当前状态与未来工作

*   **当前状态**：
    *   项目框架搭建完成。
    *   前后端基本交互流程实现。
    *   文件上传（包括ZIP）、下载、会话管理功能可用。
    *   **LLM分析和文件内容提取部分当前为模拟实现** (`SIMULATE_LLM=True`)。
    *   PDF报告生成依赖WeasyPrint。
*   **未来工作 / 核心功能实现**：
    *   **真实文件解析**：在 `core/file_parser.py` 中实现对PDF, DOCX, MD等文件的实际文本提取逻辑。
        *   集成 `pdfplumber` 进行更精确的PDF文本和结构提取。
        *   集成 `pytesseract` 实现PDF的OCR功能。
    *   **真实LLM集成**：在 `core/llm_analyzer.py` 中实现与LLM API的实际交互。
        *   使用 `prompts/prompt_templates.py` 中的模板构建请求。
        *   调用LLM进行专利摘要、核心权利要求提取、侵权对比分析。
    *   **报告生成逻辑**：在 `core/report_generator.py` 中根据LLM的真实输出来构建详细报告。
    *   **错误处理与日志**：增强应用的健壮性和可调试性。
    *   **异步任务处理**：对于耗时的LLM分析和文件处理，应使用任务队列（如Celery）进行异步处理，而不是当前的线程模拟。
    *   **安全性**：进一步加固文件上传、处理和API密钥管理。
    *   **测试**：编写单元测试和集成测试。

## 6. 注意事项

*   当前 `app.py` 中的 `simulate_analysis_and_create_report` 函数用于演示端到端流程，它生成的是虚拟数据，并非真实的专利分析结果。要获得真实结果，需要将 `config/settings.py` 中的 `SIMULATE_LLM` 设置为 `False`，并完成上述“未来工作”中提到的核心逻辑模块的实现。
*   PDF生成功能依赖 `WeasyPrint`，其安装可能涉及额外的系统依赖。如果不需要PDF导出，可以移除相关代码和依赖。

## AGENTS.md

(目前项目中未创建AGENTS.md，如果后续有特定于AI代理开发和交互的指令，可以创建此文件。)

---

欢迎贡献和反馈！
