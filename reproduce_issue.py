
import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from nameu.core.filename_processor import get_unique_filename

def test():
    directory = "."
    artist_name = "Hatori Sama"
    
    cases = [
        "(10P-126.5M) Hatori Sama – NO.025 Diesel [NIKKE].zip",
        "(10P-57.1M) (尼尔：机械纪元・2B# 魔术师) 012. 2B Magician [Hatori Sama (奈奈紀)].zip",
        "Hatori Sama – NO.036 Lisa fanart [genshin Impact] [10P-35MB] [奈奈紀].zip",
        "(8P-49.4M) Hatori Sama – NO.034.zip",
    ]
    
    with open("results.txt", "w", encoding="utf-8") as f:
        for filename in cases:
            result = get_unique_filename(directory, filename, artist_name)
            f.write(f"Original: {filename}\n")
            f.write(f"Result:   {result}\n\n")

if __name__ == "__main__":
    test()
