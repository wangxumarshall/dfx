# LLM API密钥
OPENAI_API_KEY = "sk-YOUR_OPENAI_API_KEY_HERE"  # 或者 DeepSeek API密钥
# SERP_API_KEY = "YOUR_SERP_API_KEY_HERE" # 用于互联网搜索潜在侵权线索

# 文件上传相关配置
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'md', 'txt'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

# 报告相关配置
REPORTS_FOLDER = 'reports'

# OCR相关配置 (如果使用pytesseract)
# TESSERACT_CMD = r'C:\Program Files\Tesseract-OCR\tesseract.exe' # Windows示例, 根据实际安装路径修改
TESSERACT_CMD = 'tesseract' # Linux/macOS 示例, 确保tesseract在PATH中

# LLM 模型配置
LLM_MODEL_NAME = "gpt-3.5-turbo" # 或其他适用模型如 DeepSeek 的模型名称
# LLM_BASE_URL = "YOUR_LLM_API_BASE_URL_IF_NEEDED" # 例如 DeepSeek 的 API 地址

# 日志配置
LOG_LEVEL = "INFO"

# 模拟LLM响应（用于测试，实际部署时应为False）
SIMULATE_LLM = True
SIMULATE_LLM_DELAY = 3 # seconds
