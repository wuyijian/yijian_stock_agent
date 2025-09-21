import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import json
import logging
from email.header import Header
import time
import requests  # 添加缺失的requests库导入

class NotificationSender:
    """通知发送工具类，支持多种推送方式"""
    
    def __init__(self, config_file=None):
        """初始化通知发送器，可以从配置文件加载设置"""
        self.config = {}
        self.logger = self._setup_logger()
        
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                self.logger.info(f"从配置文件{config_file}加载设置成功")
            except Exception as e:
                self.logger.error(f"加载配置文件失败: {e}")
        else:
            # 如果配置文件不存在，创建默认配置文件模板
            if config_file:
                self.logger.warning(f"配置文件{config_file}不存在，已创建默认配置模板")
                create_config_template(config_file)
    
    def _setup_logger(self):
        """设置日志"""
        logger = logging.getLogger('notification_sender')
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger
    
    def send_server酱(self, title, content, sendkey=None):
        """使用Server酱发送微信通知（已替换为企业微信群机器人，此方法保留为兼容性）"""
        self.logger.warning("Server酱推送已被替换为企业微信群机器人推送，请使用send_wechat_work方法")
        return self.send_wechat_work(title, content)
    
    def send_wechat_work(self, title, content, webhook=None, secret=None):
        """使用企业微信群机器人发送通知"""
        try:
            wechat_config = self.config.get('wechat_work', {})
            webhook = webhook or wechat_config.get('webhook')
            secret = secret or wechat_config.get('secret')
            
            if not webhook:
                self.logger.warning("未提供企业微信群机器人的webhook，无法发送通知")
                return False
            
            # 构建消息内容
            data = {
                "msgtype": "text",
                "text": {
                    "content": f"{title}\n{content}"
                }
            }
            
            # 如果有secret，需要进行签名验证
            if secret:
                import hmac
                import hashlib
                import base64
                import urllib.parse
                
                timestamp = str(round(time.time() * 1000))
                secret_enc = secret.encode('utf-8')
                string_to_sign = f"{timestamp}\n{secret}"
                string_to_sign_enc = string_to_sign.encode('utf-8')
                hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
                sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
                
                webhook_url = f"{webhook}&timestamp={timestamp}&sign={sign}"
            else:
                webhook_url = webhook
            
            response = requests.post(webhook_url, json=data, timeout=10)
            result = response.json()
            
            if result.get('errcode') == 0:
                self.logger.info("企业微信群机器人通知发送成功")
                return True
            else:
                self.logger.error(f"企业微信群机器人通知发送失败: {result.get('errmsg')}")
                return False
        except Exception as e:
            self.logger.error(f"发送企业微信群机器人通知时出错: {e}")
            return False
    
    def send_pushplus(self, title, content, token=None):
        """使用PushPlus发送微信通知"""
        try:
            token = token or self.config.get('pushplus', {}).get('token')
            if not token:
                self.logger.warning("未提供PushPlus的token，无法发送通知")
                return False
            
            url = "http://www.pushplus.plus/send"
            data = {
                "token": token,
                "title": title,
                "content": content,
                "template": "txt"
            }
            
            response = requests.post(url, json=data, timeout=10)
            result = response.json()
            
            if result.get('code') == 200:
                self.logger.info("PushPlus通知发送成功")
                return True
            else:
                self.logger.error(f"PushPlus通知发送失败: {result.get('msg')}")
                return False
        except Exception as e:
            self.logger.error(f"PushPlus发送异常: {e}")
            return False
    
    def send_email(self, title, content, to_email=None):
        """发送邮件通知"""
        try:
            # 获取邮箱配置
            email_config = self.config.get('email', {})
            smtp_server = email_config.get('smtp_server')
            smtp_port = email_config.get('smtp_port', 465)
            username = email_config.get('username')
            password = email_config.get('password')
            from_email = email_config.get('from_email', username)
            to_email = to_email or email_config.get('to_email')
            
            # 检查配置是否完整
            if not all([smtp_server, username, password, from_email, to_email]):
                self.logger.warning("邮箱配置不完整，无法发送邮件")
                return False
            
            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = Header(from_email)
            msg['To'] = Header(to_email)
            msg['Subject'] = Header(title, 'utf-8')
            
            # 添加邮件正文
            msg.attach(MIMEText(content, 'plain', 'utf-8'))
            
            # 发送邮件
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
            server.login(username, password)
            server.send_message(msg)
            server.quit()
            
            self.logger.info("邮件发送成功")
            return True
        except Exception as e:
            self.logger.error(f"邮件发送异常: {e}")
            return False
    
    def send_dingtalk(self, title, content, access_token=None, secret=None):
        """发送钉钉机器人通知"""
        try:
            access_token = access_token or self.config.get('dingtalk', {}).get('access_token')
            secret = secret or self.config.get('dingtalk', {}).get('secret')
            
            if not access_token:
                self.logger.warning("未提供钉钉机器人的access_token，无法发送通知")
                return False
            
            import hmac
            import hashlib
            import base64
            
            # 如果提供了secret，需要进行签名
            timestamp = str(round(time.time() * 1000))
            sign = ''
            if secret:
                secret_enc = secret.encode('utf-8')
                string_to_sign = f'{timestamp}\n{secret}'
                string_to_sign_enc = string_to_sign.encode('utf-8')
                hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
                sign = base64.b64encode(hmac_code).decode('utf-8')
            
            url = f"https://oapi.dingtalk.com/robot/send?access_token={access_token}"
            if secret:
                url += f"&timestamp={timestamp}&sign={sign}"
            
            data = {
                "msgtype": "text",
                "text": {
                    "content": f"{title}\n{content}"
                }
            }
            
            response = requests.post(url, json=data, timeout=10)
            result = response.json()
            
            if result.get('errcode') == 0:
                self.logger.info("钉钉通知发送成功")
                return True
            else:
                self.logger.error(f"钉钉通知发送失败: {result.get('errmsg')}")
                return False
        except Exception as e:
            self.logger.error(f"钉钉发送异常: {e}")
            return False
    
    def send_notification(self, title, content, methods=None):
        """统一发送通知接口，仅支持企业微信群机器人通知"""
        results = {}
        
        # 只使用企业微信群机器人通知
        if self.config.get('wechat_work', {}).get('webhook'):
            results['wechat_work'] = self.send_wechat_work(title, content)
        else:
            # 如果没有配置企业微信群机器人，打印通知内容到控制台
            self.logger.info(f"未配置企业微信群机器人，以下是通知内容:\n标题: {title}\n内容:\n{content}")
            results['console'] = True
        
        return results

# 添加配置模板创建函数
def create_config_template(config_file='notification_config.json'):
    """创建通知配置文件模板"""
    template = {
        "wechat_work": {
            "webhook": "your_wechat_work_webhook",
            "secret": "your_wechat_work_secret"  # 可选，用于签名验证
        },
        "pushplus": {
            "token": "your_pushplus_token"
        },
        "email": {
            "smtp_server": "smtp.example.com",
            "smtp_port": 465,
            "username": "your_email@example.com",
            "password": "your_email_password",
            "from_email": "your_email@example.com",
            "to_email": "recipient@example.com"
        },
        "dingtalk": {
            "access_token": "your_dingtalk_access_token",
            "secret": "your_dingtalk_secret"
        }
    }
    
    try:
        # 确保目录存在
        config_dir = os.path.dirname(config_file)
        if config_dir and not os.path.exists(config_dir):
            os.makedirs(config_dir)
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(template, f, ensure_ascii=False, indent=4)
        
        print(f"配置文件模板已创建: {config_file}")
        print("请根据需要修改配置文件中的各项参数")
        print("注意：Server酱推送已被替换为企业微信群机器人推送，请配置wechat_work部分")
    except Exception as e:
        print(f"创建配置文件模板时出错: {e}")

# 确保兼容性，添加别名方法
def send_notification(title, message):
    """兼容旧版的通知发送函数"""
    sender = NotificationSender()
    return sender.send_notification(title, message)

if __name__ == "__main__":
    # 创建配置文件模板
    create_config_template()
    
    # 示例用法
    print("\n===== 通知发送示例 =====")
    sender = NotificationSender("./notification_config.json")
    
    # 测试通知
    title = "测试通知"
    content = "这是一条测试消息，用于验证通知发送功能是否正常工作。\n\n测试时间: " + time.strftime("%Y-%m-%d %H:%M:%S")
    
    print("\n尝试发送测试通知（由于没有配置，只会打印到控制台）:")
    sender.send_notification(title, content)
    
    print("\n===== 示例结束 =====")