# 安装 pip install pydantic-settings 用与设置环境变量
from pydantic_settings import BaseSettings, SettingsConfigDict

class Setting(BaseSettings):
    database_hostname: str    # ip地址
    database_port: int    # 端口
    database_username: str    # 用户名
    database_password: str    # 密码
    database_name: str    # 数据库名称 
    session_secret_key: str  # 会话密钥
    redis_ip: str         # redis的ip
    redis_port: str       # redis的端口
    redis_db: str         # redis的数据库
    redis_password: str   # redis的密码

    # 用于找到.env文件, 匹配到Settings类中
    model_config = SettingsConfigDict(
        env_file=".env",          # 指定 .env 文件路径
        env_file_encoding="utf-8",
        # env_prefix="MYAPP_"     # 如果有前缀，可以设置
    )
    
settings = Setting()
