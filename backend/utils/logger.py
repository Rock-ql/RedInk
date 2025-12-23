"""醒目的日志工具类"""
import logging
from typing import Optional

# ANSI 颜色代码
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'


class DetailedLogger:
    """提供醒目格式的日志工具"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    @staticmethod
    def _format_box(title: str, content: list, color: str = Colors.CYAN) -> str:
        """创建带边框的文本块"""
        max_len = max(len(title), max(len(line) for line in content)) + 4
        border = "=" * max_len

        lines = [
            f"\n{color}{Colors.BOLD}{border}",
            f"  {title}",
            f"{border}{Colors.RESET}"
        ]

        for line in content:
            lines.append(f"{color}{line}{Colors.RESET}")

        lines.append(f"{color}{border}{Colors.RESET}\n")
        return "\n".join(lines)

    def log_outline_start(self, topic: str, has_images: bool, image_count: int = 0):
        """记录大纲生成开始"""
        content = [
            f"📝 主题: {topic[:100]}{'...' if len(topic) > 100 else ''}",
            f"🖼️  参考图片: {'是 (' + str(image_count) + ' 张)' if has_images else '否'}",
            f"⏰ 开始时间: {self._get_timestamp()}"
        ]
        message = self._format_box("🚀 开始生成大纲", content, Colors.CYAN)
        self.logger.info(message)

    def log_outline_api_call(self, provider: str, model: str, temperature: float,
                            max_tokens: int, prompt_length: int):
        """记录大纲生成 API 调用详情"""
        content = [
            f"🔌 服务商: {provider}",
            f"🤖 模型: {model}",
            f"🌡️  温度: {temperature}",
            f"📏 最大Token: {max_tokens}",
            f"📝 提示词长度: {prompt_length} 字符"
        ]
        message = self._format_box("📡 调用文本生成 API", content, Colors.BLUE)
        self.logger.info(message)

    def log_outline_success(self, outline_length: int, page_count: int, elapsed_time: float):
        """记录大纲生成成功"""
        content = [
            f"✅ 状态: 成功",
            f"📄 生成字数: {outline_length} 字符",
            f"📑 页面数量: {page_count} 页",
            f"⏱️  耗时: {elapsed_time:.2f} 秒"
        ]
        message = self._format_box("🎉 大纲生成完成", content, Colors.GREEN)
        self.logger.info(message)

    def log_outline_error(self, error_msg: str, error_type: str = "未知错误"):
        """记录大纲生成失败"""
        content = [
            f"❌ 错误类型: {error_type}",
            f"💬 错误信息: {error_msg[:200]}{'...' if len(error_msg) > 200 else ''}"
        ]
        message = self._format_box("⚠️  大纲生成失败", content, Colors.RED)
        self.logger.error(message)

    def log_image_generation_start(self, task_id: str, total_pages: int, use_reference: bool):
        """记录图片生成任务开始"""
        content = [
            f"🎯 任务ID: {task_id}",
            f"📊 总页数: {total_pages}",
            f"🖼️  使用参考图: {'是' if use_reference else '否'}",
            f"⏰ 开始时间: {self._get_timestamp()}"
        ]
        message = self._format_box("🚀 开始批量生成图片", content, Colors.CYAN)
        self.logger.info(message)

    def log_image_api_call(self, index: int, page_type: str, provider: str,
                          model: str, prompt_length: int, has_reference: bool,
                          attempt: int = 1, max_attempts: int = 1):
        """记录单张图片 API 调用"""
        retry_info = f" (重试 {attempt}/{max_attempts})" if max_attempts > 1 else ""
        content = [
            f"📄 页面: P{index + 1} ({page_type}){retry_info}",
            f"🔌 服务商: {provider}",
            f"🤖 模型: {model}",
            f"📝 提示词长度: {prompt_length} 字符",
            f"🖼️  使用参考图: {'是' if has_reference else '否'}"
        ]
        message = self._format_box(f"📡 调用图片生成 API - P{index + 1}", content, Colors.BLUE)
        self.logger.info(message)

    def log_image_success(self, index: int, filename: str, file_size: int,
                         compressed: bool, elapsed_time: float):
        """记录单张图片生成成功"""
        size_mb = file_size / (1024 * 1024)
        content = [
            f"✅ 状态: 成功",
            f"📄 页面: P{index + 1}",
            f"📁 文件名: {filename}",
            f"💾 文件大小: {size_mb:.2f} MB",
            f"🗜️  已压缩: {'是' if compressed else '否'}",
            f"⏱️  耗时: {elapsed_time:.2f} 秒"
        ]
        message = self._format_box(f"✨ 图片生成成功 - P{index + 1}", content, Colors.GREEN)
        self.logger.info(message)

    def log_image_error(self, index: int, error_msg: str, will_retry: bool = False):
        """记录单张图片生成失败"""
        status = "将重试" if will_retry else "已失败"
        content = [
            f"❌ 状态: {status}",
            f"📄 页面: P{index + 1}",
            f"💬 错误信息: {error_msg[:200]}{'...' if len(error_msg) > 200 else ''}"
        ]
        color = Colors.YELLOW if will_retry else Colors.RED
        title = f"⚠️  图片生成{'重试' if will_retry else '失败'} - P{index + 1}"
        message = self._format_box(title, content, color)
        self.logger.warning(message) if will_retry else self.logger.error(message)

    def log_batch_complete(self, total: int, success: int, failed: int, elapsed_time: float):
        """记录批量生成完成"""
        success_rate = (success / total * 100) if total > 0 else 0
        content = [
            f"📊 总计: {total} 张",
            f"✅ 成功: {success} 张",
            f"❌ 失败: {failed} 张",
            f"📈 成功率: {success_rate:.1f}%",
            f"⏱️  总耗时: {elapsed_time:.2f} 秒"
        ]
        color = Colors.GREEN if failed == 0 else Colors.YELLOW
        message = self._format_box("🏁 批量生成完成", content, color)
        self.logger.info(message)

    @staticmethod
    def _get_timestamp() -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_detailed_logger(logger_name: str) -> DetailedLogger:
    """获取详细日志记录器"""
    logger = logging.getLogger(logger_name)
    return DetailedLogger(logger)
