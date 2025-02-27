import os
import datetime
from auditok import split


def format_timestamp(seconds):
    """将秒转换为SRT时间戳格式 (HH:MM:SS,mmm)"""
    time_obj = datetime.timedelta(seconds=seconds)
    hours, remainder = divmod(time_obj.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int(time_obj.microseconds / 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def generate_srt(audio_regions, output_file):
    """根据音频区域生成SRT文件"""
    with open(output_file, "w", encoding="utf-8") as f:
        for i, region in enumerate(audio_regions):
            # 序号
            f.write(f"{i+1}\n")
            # 时间码
            start_time = format_timestamp(region.meta.start)
            end_time = format_timestamp(region.meta.end)
            f.write(f"{start_time} --> {end_time}\n")
            # 字幕内容（暂时填写为xxx）
            f.write("xxx\n\n")


def process_audio(
    audio_file,
    output_file=None,
    min_dur=0.5,
    max_dur=10,
    max_silence=0.3,
    energy_threshold=55,
):
    # 确定输出文件路径
    if output_file is None:
        base_name = os.path.splitext(audio_file)[0]
        output_file = f"{base_name}.srt"

    print(f"Processing audio file: {audio_file}")
    print(f"Min duration: {min_dur}s")
    print(f"Max duration: {max_dur}s")
    print(f"Max silence: {max_silence}s")
    print(f"Energy threshold: {energy_threshold}")

    # 分割音频
    audio_regions = list(
        split(
            audio_file,
            min_dur=min_dur,
            max_dur=max_dur,
            max_silence=max_silence,
            energy_threshold=energy_threshold,
        )
    )

    # 打印分割信息
    print(f"Found {len(audio_regions)} audio segments")
    for i, region in enumerate(audio_regions):
        print(
            f"Region {i+1}: {region.meta.start:.3f}s - {region.meta.end:.3f}s = {region.duration:.3f}s"
        )

    # 生成SRT文件
    generate_srt(audio_regions, output_file)
    print(f"SRT file saved to: {output_file}")


if __name__ == "__main__":
    # 使用默认参数直接执行
    audio_file = "Section 1.mp3"  # 替换为你的音频文件路径
    process_audio(audio_file)
