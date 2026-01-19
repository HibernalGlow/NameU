
import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from nameu.core.filename_processor import get_unique_filename

def test():
    directory = "."
    artist_name = "Hatori Sama"
    
    with open("results.txt", "w", encoding="utf-8") as f:
        # Case 1: Size prefix
        filename1 = "(10P-57.1M) (尼尔：机械纪元・2B# 魔术师) 012. 2B Magician [Hatori Sama (奈奈紀)][samename_1].zip"
        result1 = get_unique_filename(directory, filename1, artist_name)
        f.write(f"Case 1 Original: {filename1}\n")
        f.write(f"Case 1 Result:   {result1}\n\n")

        # Case 2: Dot prefix with digits (should stay in prefix)
        filename2 = "(尼尔：机械纪元・2B# 魔术师) 012. 2B Magician.zip"
        result2 = get_unique_filename(directory, filename2, artist_name)
        f.write(f"Case 2 Original: {filename2}\n")
        f.write(f"Case 2 Result:   {result2}\n\n")

        # Case 3: Dot prefix WITHOUT digits (currently might move to middle/suffix)
        filename3 = "(尼尔：机械纪元・魔术师) 012. 2B Magician.zip"
        result3 = get_unique_filename(directory, filename3, artist_name)
        f.write(f"Case 3 Original: {filename3}\n")
        f.write(f"Case 3 Result:   {result3}\n")

if __name__ == "__main__":
    test()
