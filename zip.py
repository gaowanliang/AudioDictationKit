import os
import subprocess
import argparse
import logging
from pathlib import Path
import tempfile
import shutil

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def compress_audio(file_path, output_path=None, bitrate="128k"):
    """
    使用ffmpeg压缩音频文件
    :param file_path: 原始文件路径
    :param output_path: 输出文件路径，默认为临时文件
    :param bitrate: 目标比特率，默认128k
    :return: 是否成功压缩
    """
    # 创建一个临时文件夹中的临时文件
    temp_dir = tempfile.gettempdir()
    file_name = os.path.basename(file_path)
    temp_file = os.path.join(temp_dir, f"ffmpeg_temp_{os.urandom(8).hex()}_{file_name}")

    try:
        # 构建ffmpeg命令
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            file_path,
            "-c:a",
            "aac" if file_path.lower().endswith(".m4a") else "libmp3lame",
            "-b:a",
            bitrate,
            temp_file,
        ]

        # 执行命令
        logger.debug(f"执行命令: {' '.join(cmd)}")
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )

        if result.returncode != 0:
            logger.error(f"压缩失败: {file_path}")
            logger.error(f"错误信息: {result.stderr}")
            return False

        # 获取原始文件大小
        original_size = os.path.getsize(file_path)
        compressed_size = os.path.getsize(temp_file)

        # 安全地替换原始文件
        try:
            # 使用shutil实现更可靠的文件复制
            shutil.copy2(temp_file, file_path)

            # 计算压缩比例
            saving = (original_size - compressed_size) / original_size * 100
            logger.info(f"文件: {file_path}")
            logger.info(
                f"原始大小: {original_size/1024/1024:.2f}MB, 压缩后: {compressed_size/1024/1024:.2f}MB, 节省: {saving:.2f}%"
            )

            return True
        except Exception as e:
            logger.error(f"替换原始文件时出错: {str(e)}")
            return False

    except Exception as e:
        logger.error(f"处理文件 {file_path} 时出错: {str(e)}")
        return False
    finally:
        # 清理临时文件
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except Exception as e:
            logger.warning(f"删除临时文件 {temp_file} 时出错: {str(e)}")


def process_directory(directory, bitrate="128k"):
    """
    递归处理目录中的所有音频文件
    :param directory: 要处理的目录
    :param bitrate: 目标比特率
    """
    count = {"processed": 0, "failed": 0, "skipped": 0, "total": 0}

    # 先统计总文件数
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith((".mp3", ".m4a")):
                count["total"] += 1

    processed = 0

    # 处理文件
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith((".mp3", ".m4a")):
                file_path = os.path.join(root, file)
                processed += 1
                logger.info(f"处理文件 [{processed}/{count['total']}]: {file_path}")

                try:
                    if compress_audio(file_path, bitrate=bitrate):
                        count["processed"] += 1
                    else:
                        count["failed"] += 1
                except Exception as e:
                    logger.error(f"处理时发生异常: {str(e)}")
                    count["failed"] += 1
            else:
                count["skipped"] += 1

    return count


def main():
    parser = argparse.ArgumentParser(description="压缩音频文件(MP3和M4A)并替换原始文件")
    parser.add_argument("directory", type=str, help="要处理的目录路径")
    parser.add_argument(
        "--bitrate", type=str, default="128k", help="目标比特率，例如: 128k, 192k, 256k"
    )

    args = parser.parse_args()

    if not os.path.isdir(args.directory):
        logger.error(f"目录不存在: {args.directory}")
        return

    logger.info(f"开始处理目录: {args.directory}, 目标比特率: {args.bitrate}")

    # 检查ffmpeg是否可用
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        logger.error("错误: ffmpeg未安装或不在系统PATH中。请安装ffmpeg后重试。")
        return

    # 处理目录
    stats = process_directory(args.directory, args.bitrate)

    logger.info(f"处理完成!")
    logger.info(f"已压缩: {stats['processed']} 文件")
    logger.info(f"失败: {stats['failed']} 文件")
    logger.info(f"已跳过: {stats['skipped']} 文件（非mp3/m4a）")


if __name__ == "__main__":
    main()
