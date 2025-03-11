import asyncio
import os
import wave
import struct
from pydub import AudioSegment
import edge_tts

# 更改为使用输入文件
INPUT_FILE = "add.txt"
OUTPUT_DIR = "temp_audio"
FINAL_OUTPUT = "final_output.mp3"
VOICE = "en-GB-SoniaNeural"


async def generate_audio(text, output_file):
    """为单行文本生成音频"""
    communicate = edge_tts.Communicate(text, VOICE)
    submaker = edge_tts.SubMaker()
    with open(output_file, "wb") as file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                submaker.feed(chunk)


def create_silence(seconds, output_file):
    """创建指定秒数的静音文件"""
    # 44100Hz, 16bit, mono
    sample_rate = 44100
    silence = AudioSegment.silent(duration=seconds * 1000)  # pydub使用毫秒
    silence.export(output_file, format="mp3")


def combine_audio_files(file_list, output_file):
    """合并所有音频文件"""
    combined = AudioSegment.empty()
    silence = AudioSegment.silent(duration=4000)  # 4秒静音

    for i, file in enumerate(file_list):
        audio = AudioSegment.from_mp3(file)
        combined += audio

        # 在最后一个文件之后不添加静音
        if i < len(file_list) - 1:
            combined += silence

    combined.export(output_file, format="mp3")


async def amain() -> None:
    """Main function"""
    # 确保输出目录存在
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # 读取输入文件的每一行
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    audio_files = []
    max_retries = 5

    # 为每一行生成音频
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:  # 跳过空行
            continue

        # 生成文件名，格式为00001.mp3
        output_file = os.path.join(OUTPUT_DIR, f"{i+1:05d}.mp3")

        # 检查文件是否已存在
        if os.path.exists(output_file):
            print(f"文件 {output_file} 已存在，跳过生成")
            audio_files.append(output_file)
            continue

        print(f"正在生成第 {i+1} 个音频: {line}")

        # 指数退避重试
        retry_count = 0
        while retry_count < max_retries:
            try:
                await generate_audio(line, output_file)
                audio_files.append(output_file)
                break
            except Exception as e:
                retry_count += 1
                wait_time = 2**retry_count  # 指数退避：1, 2, 4, 8, 16秒
                print(f"生成音频出错: {e}, 第{retry_count}次重试, 等待{wait_time}秒")
                await asyncio.sleep(wait_time)

        if retry_count == max_retries:
            print(f"达到最大重试次数，跳过音频 {i+1}")
            # 删除生成的文件
            if os.path.exists(output_file):
                os.remove(output_file)

    # 合并所有音频文件
    if audio_files:
        print("正在合并所有音频文件...")
        combine_audio_files(audio_files, FINAL_OUTPUT)
        print(f"完成! 最终文件已保存为 {FINAL_OUTPUT}")


if __name__ == "__main__":
    asyncio.run(amain())
