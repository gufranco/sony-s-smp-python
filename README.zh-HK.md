# Sony S-SMP

以 Python 實現的 Super Nintendo Sony S-SMP 音效單元：一個 SPC700 處理器與一個 S-DSP 聲音產生器，共用 64 KB 記憶體、四個連接埠、三個計時器和一個 64 位元組的開機程式，並以該開機程式及數值在主機上實測取得的檢查作為標準。

[English](README.md) | [日本語](README.ja.md) | [简体中文](README.zh-Hans.md) | 繁體中文（香港）

[![CI](https://github.com/gufranco/sony-s-smp-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/sony-s-smp-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/sony-s-smp-python)](https://github.com/gufranco/sony-s-smp-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**4** 個連接埠就是與主機之間的全部介面，**3** 項附有在主機上實測數值的檢查，**0** 項不符，一個檢查卡帶的 **18** 項判定全部相符，**898** 項測試，**100%** 語句與分支覆蓋率，無任何依賴

```python
import ssmp

unit = ssmp.Chip("ssmp").reset()
unit.run_for(6300)
print(hex(unit.read(0)), hex(unit.read(1)))

unit.write(0, 0xCC)
unit.run_for(64)
print(hex(unit.read(0)))
```

```
0xaa 0xbb
0xcc
```

單元執行開機程式 6,300 個週期後，在連接埠 0 回應 `0xaa`，在連接埠 1 回應 `0xbb`。每部 Super Nintendo 都要等到這兩個位元組出現，才會向音效硬件傳送任何東西。接着主機把 `0xcc` 寫入連接埠 0，64 個週期後開機程式將其回傳，表示已準備好接收一個區塊。

## 安裝

| 需求     | 版本                         |
| :------- | :--------------------------- |
| Python   | 3.12 或更新                  |
| git      | 任何版本，用於取得兩個子模組 |
| 開機程式 | 一份你已擁有的 64 位元組副本 |

```bash
git clone --recurse-submodules https://github.com/gufranco/sony-s-smp-python.git
cd sony-s-smp-python
python3 ssmp/doctor.py
```

套件不匯入標準程式庫以外的任何東西。處理器是 [sony-spc700-python](https://github.com/gufranco/sony-spc700-python)，聲音產生器是 [sony-s-dsp-python](https://github.com/gufranco/sony-s-dsp-python)，兩者都以子模組形式簽出。缺少它們便無法建立任何東西，`git submodule update --init --recursive` 會把它們取回。

開機程式屬於 Sony，不在本儲存庫內。請把副本放在 `boot/`、本簽出所在目錄的 `boot/`，或 `SSMP_BOOT_DIR` 指定的任何目錄。在沒有副本的機器上，每個以它建立單元的範例都會拒絕執行，並以一句話說明缺少甚麼。

診斷腳本會檢查機器和簽出內容，建立單元，最後輸出一行。當所有關於套件的檢查結果都通過時，它以 0 結束，否則以 1 結束。提交錯誤報告時請貼上其完整輸出。兩個子模組和開機程式都齊備時，它的結尾是：

```
  5 checks, nothing to report
```

安裝套件時也會以 `ssmp-doctor` 的名稱安裝同一份報告。

版本遵循 [Semantic Versioning](https://semver.org/)，由 semantic-release 根據提交歷史發佈。每個版本都有標籤，並列在[版本頁面](https://github.com/gufranco/sony-s-smp-python/releases)上。

## 介面

`ssmp.Chip(model, boot=None, identity=None, images=None, fill=None, seed=None)` 建立一個處於剛通電狀態的單元：處理器、聲音產生器、記憶體、十六個暫存器、連接埠、計時器以及驅動計時器的預分頻器都由同一個種子打亂，甚麼都不清零，在呼叫 `reset()` 之前甚麼都不會執行。`model` 為必填。

| 參數       | 含義                                                                                                     |
| :--------- | :------------------------------------------------------------------------------------------------------- |
| `model`    | 型號名稱。大小寫及分隔符 `-`、`_`、`.` 和空格都會被忽略，因此 `"S-SMP"` 和 `"s_smp"` 都會建立 `ssmp`     |
| `boot`     | 開機程式的 64 個位元組。省略時，單元會搜尋開機目錄，並以 SHA-256 識別找到的檔案                          |
| `identity` | 所提供 `boot` 的記錄。省略時記錄為 `supplied`                                                            |
| `images`   | 用以取代開機目錄進行搜尋的目錄冊，以型號名稱為鍵                                                         |
| `fill`     | 通電時用來填充處理器記憶體的位元組。省略時為隨機打亂的內容                                               |
| `seed`     | 產生全部打亂內容的種子。省略時為處理器的 `UNSET_SEED`，即 `0x5A5A5A5A`。同一個種子每次都建立出同一個單元 |

### 呼叫

| 呼叫                  | 作用                                                                                                                                                                                                                             |
| :-------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `reset()`             | 即主機的重設線。顯示開機程式視窗，然後重設聲音產生器和處理器，處理器隨即開始執行開機程式。按 Nintendo 的 Book I 所載，停止全部三個計時器。記憶體、計時器的分頻值、級數和計數器、預分頻器、連接埠和其他暫存器保持原值。傳回該單元 |
| `step()`              | 執行一條處理器指令。傳回所用的週期數                                                                                                                                                                                             |
| `run_for(cycles)`     | 執行指令，直至至少經過 `cycles` 個週期。傳回所耗的週期數                                                                                                                                                                         |
| `read(index)`         | 主機在連接埠 `index`（0 至 3）讀到的內容：單元最後寫入該處的位元組                                                                                                                                                               |
| `write(index, value)` | 主機寫入連接埠 `index` 的內容：單元在該處讀到的位元組                                                                                                                                                                            |

### 狀態

| 屬性        | 含義                                                              |
| :---------- | :---------------------------------------------------------------- |
| `model`     | 標準型號名稱                                                      |
| `part`      | 同一名稱，按開機目錄冊所用的鍵                                    |
| `identity`  | 開機程式的記錄：`part`、`processor`、`revision`、`bytes_long`     |
| `cycles`    | 自單元建立以來的處理器週期數。重設不會將其清零                    |
| `processor` | 來自處理器子模組的 SPC700                                         |
| `dsp`       | 來自聲音產生器子模組的 S-DSP                                      |
| `space`     | 處理器看到的 64 KB，16 個暫存器位於 `$00F0`，開機窗口位於 `$FFC0` |

`processor`、`dsp` 和 `space` 能觸及主機無法觸及的範圍。驅動它們的檢查是在檢查模型，而不是晶片本身。

### 模組內容

| 名稱                                        | 內容                                                                                                                                                                                                     |
| :------------------------------------------ | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ssmp.MODELS`                               | 唯一的 `Model` 記錄，以名稱為鍵                                                                                                                                                                          |
| `ssmp.Model`                                | 含有 `name`、`summary`、`processor`、`memory` 和 `boot` 的記錄                                                                                                                                           |
| `ssmp.why_not(held=None)`                   | 若在此處可以建立單元則為 `None`，否則為說明缺少甚麼的句子。`held` 是用來代替搜尋作判斷的目錄，形狀與 `available()` 的回傳值相同                                                                          |
| `ssmp.available(held=None, catalogue=None)` | 在此處找到的開機程式，以型號名稱為鍵。提供 `held` 時不作搜尋，原樣交回。`catalogue` 是與 [`ssmp/artifacts.manifest.json`](ssmp/artifacts.manifest.json) 形狀相同的清單，用來代替本套件附帶的清單辨認檔案 |
| `ssmp.identify(image, catalogue=None)`      | 開機程式位元組的記錄，帶有 `part`、`processor`、`revision` 和 `bytes_long`。會拋出 `Unrecognised` 或 `Corrupt`，有修正方法時會指出。`catalogue` 與 `available()` 相同                                    |
| `ssmp.VERSION`、`ssmp.__version__`          | 已安裝的版本                                                                                                                                                                                             |

| 錯誤                     | 引發時機                                                                                            |
| :----------------------- | :-------------------------------------------------------------------------------------------------- |
| `ssmp.UnknownModelError` | 沒有指定型號，或該名稱不在本套件涵蓋範圍內。訊息會列出現有的名稱                                    |
| `ssmp.NoBootRom`         | 某個子模組未簽出，或找不到該型號的開機程式                                                          |
| `ssmp.WrongShape`        | 開機程式不是剛好 64 個位元組                                                                        |
| `ssmp.Unrecognised`      | 檔案的 SHA-256 與 [`ssmp/artifacts.manifest.json`](ssmp/artifacts.manifest.json) 中任何項目都不相符 |
| `ssmp.Corrupt`           | 檔案的 SHA-256 相符，但另一個已公佈的摘要不符，或與已記錄的損壞傾印相符                             |

```python
import ssmp

for name in (None, "s-dsp"):
    try:
        ssmp.Chip(name)
    except ssmp.UnknownModelError as error:
        print(error)

try:
    ssmp.Chip("ssmp", boot=bytes(10))
except ssmp.WrongShape as error:
    print(error)

try:
    ssmp.identify(bytes(100))
except ssmp.Unrecognised as error:
    print(error)
```

```
no model was named, and this package will not choose one for you. Name one of: ssmp
s-dsp is not a unit this package covers; there is ssmp
a boot program is exactly 64 bytes and this one is 10
nothing in the manifest has sha256 cd00e292c5970d3c5e2f0ffa5171e555bc46bfc4faddfb4a418b6840b86e79a3. It is 100 bytes and a boot program is 64, so this is not one of them at all.
```

若檔案是正確的程式但形式不對，訊息會改為指出修正方法：把它當作十六進位列表讀取，或取較大檔案的首 64 個或末 64 個位元組。

### 一個連接埠是兩個位元組

```python
import ssmp

unit = ssmp.Chip("ssmp").reset()
unit.run_for(6300)
unit.write(2, 0x55)
print(unit.read(2), unit.space.read8(0xF6))
```

```
200 85
```

每個連接埠保存一個由主機送往單元的位元組，以及一個由單元送往主機的位元組。主機向連接埠 2 寫入 `0x55`，讀回的是 200，這是通電時留在那裡的值，因為開機程式從不寫連接埠 2，而單元在 `$F6` 讀到 85。每個連接埠只保存一個位元組的模型，在兩次寫入交錯之前都能通過，之後便會交給雙方一個雙方都沒有傳送過的值。

### 計時器

```python
import ssmp

unit = ssmp.Chip("ssmp", boot=bytes(64))
space = unit.space
space.write8(0xFA, 0)
space.write8(0xFC, 2)
space.write8(0xF1, 0x85)

space.spend(128 * 256 * 3)
print(space.read8(0xFD), space.read8(0xFD))

space.write8(0xF1, 0x80)
space.write8(0xF1, 0x84)
space.spend(16 * 2 * 20)
print(space.read8(0xFF))
print([space.read8(address) for address in (0xF0, 0xF1, 0xFA, 0xFB, 0xFC)])
```

```
3 0
4
[0, 0, 0, 0, 0]
```

此範例以 64 個零位元組建立單元，因此在沒有開機程式的機器上也能執行，並直接驅動暫存器空間。計時器 0 和 1 每 128 個處理器週期走一個節拍，計時器 2 每 16 個週期走一個節拍。每個計時器把節拍數除以寫入其位於 `$FA` 至 `$FC` 的除數，除數為 0 時以 256 相除。向位於 `$F1` 的控制暫存器寫入 `0x85`，會啟用計時器 0 和 2，並保持開機窗口可見。

計時器 0 在 98,304 個週期內數到 3，而讀取會清除其計數器，因此第二次讀取得到 0。計時器 2 數到 20，讀出的是 4，因為計數器只有四個位元。測試暫存器、控制暫存器和三個除數只寫不讀：五者都回應 0。對這十六個暫存器的每次寫入，也會落到其下方的記憶體，聲音產生器直接讀取那片記憶體。

| 位址           | 暫存器                                                                                                        |
| :------------- | :------------------------------------------------------------------------------------------------------------ |
| `$F0`          | 測試。讀出 0                                                                                                  |
| `$F1`          | 控制：位元 0 至 2 為計時器啟用，位元 4 清除連接埠 0 和 1，位元 5 清除連接埠 2 和 3，位元 7 為開機窗口。讀出 0 |
| `$F2`、`$F3`   | 聲音產生器的位址和數據                                                                                        |
| `$F4` 至 `$F7` | 連接埠 0 至 3                                                                                                 |
| `$F8`、`$F9`   | 備用暫存器。無論其下方記憶體保存甚麼，都讀回最後寫入的位元組                                                  |
| `$FA` 至 `$FC` | 計時器除數。讀出 0                                                                                            |
| `$FD` 至 `$FF` | 計時器計數器，讀取時清除                                                                                      |

### 命令列工具

| 命令                                     | 作用                                          | 結束碼                                                       |
| :--------------------------------------- | :-------------------------------------------- | :----------------------------------------------------------- |
| `python3 ssmp/doctor.py`                 | 報告機器和簽出內容，然後建立並重設單元        | 0 沒有需要報告的事項，1 有檢查結果未通過                     |
| `python3 -m conformance.against_checks`  | 以 Shay Green 的三項檢查測試單元              | 0 全部相符，1 有一項不符或與其摘要不相符，2 沒有檢查任何東西 |
| `python3 -m conformance.speed`           | 量度每秒處理器週期數，下限為 20,000           | 0 達到或高於下限，1 低於下限，2 沒有量度任何東西             |
| `python3 -m conformance.quotes`          | 在記錄所引用的手冊中找出記錄引用的每一句      | 0 全部引文都找到，或本機沒有手冊；1 其他情況                 |
| `python3 -m conformance.links`           | 探測本 README 中的每個位址，並輸出 JSON 報告  | 0 沒有失效，1 有位址回應 404 或 410                          |
| `python3 -m conformance.package <wheel>` | 檢查已建置的 wheel 是否包含每個模組且不含測試 | 0 正常，1 有錯誤或檔案不存在，2 沒有指定 wheel               |

## 合併兩半時發現的問題

兩半都不模擬對方，因為同一條線路有兩個模型，正是兩個模型產生分歧的原因。把它們合在一起時，發現了處理器的一個缺陷。

處理器在重設時打亂所有旗標，理由是其手冊沒有給出通電時的值。開機程式以 `mov $f4,#$aa` 和 `mov $f5,#$bb` 回應主機，而這兩條指令只有在直接頁為零頁時才會到達連接埠。若直接頁旗標被設定，它們會寫入位於 `$01f4` 的普通記憶體，握手永遠不會出現，任何卡帶都無法上載其音效程式。修正已併入 [sony-spc700-python](https://github.com/gufranco/sony-spc700-python)：重設後該旗標為清除狀態。

## 在硬件上實測的檢查發現的問題

五個只寫不讀的暫存器，回應的是其下方的記憶體內容。

`initial_regs.spc` 依次讀取全部十六個暫存器，並把結果的校驗和與其作者在主機上實測的值比較。在這五個暫存器的所有排列中，只有一種能重現該校驗和：五者都回應 0。[SNESdev wiki](https://snes.nesdev.org/wiki/S-SMP) 以文字說明了同一結論。

其後把舊行為放回去，以觀察檢查失敗。它在子檢查 3 不符，報告 `d57e2579`，而期望值是 `9d4d2100`。另外兩項檢查仍然相符，因為兩者都不讀取這些暫存器。

## 一個單元，而不是放在同一盒子裏的兩半

處理器和聲音產生器讀取同一個 64 KB，因為實際晶片上就是如此。各聲部從中取出壓縮區塊，回聲單元則把數據寫回其中。若兩半各有一份儲存，程式上載的每個取樣都會遺失。

處理器每走一個週期，產生器就走一個時脈。[`ssmp/rates.py`](ssmp/rates.py) 推導出這一點，而不是直接設定：同一個晶體經除數 24 到達處理器，經 768 到達產生器，每個取樣內含 32 個時脈。24 乘以 32 等於 768，兩者都得出每秒 1,024,000。

```python
from ssmp import rates

print(rates.PROCESSOR_HZ, rates.GENERATOR_HZ, rates.GENERATOR_CLOCKS)
print(rates.SLOW_TIMER_CYCLES, rates.FAST_TIMER_CYCLES)
```

```
1024000 1024000 1
128 16
```

建立單元時，產生器和處理器一樣處於被打亂的狀態。主機的重設線同時連接到兩者，所以 `reset()` 會重設兩者。處於重設狀態的產生器不會寫入回聲。未被重設的產生器照常接收時脈，如果它被打亂的旗標暫存器開啟了回聲寫入，它就會寫到被打亂的回聲暫存器所指向的位置。這一點如實建模而不加阻止，至於真實單元是否如此、怎樣才能確定，見 [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md)。

## 未模擬的部分

- **本單元時脈與主機時脈之間的任何比率。** 兩者由各自的晶體驅動，彼此不能整除，因此比率是個別主機板的屬性。沒有公佈任何數字，也不以主機週期提供任何經過時間。上文的比率是同一晶體上兩半之間的比率。
- **處理器和聲音產生器。** 兩者各自是獨立的成員，在此以子模組形式使用。
- **主機。** [`conformance/console.py`](conformance/console.py) 在檢查中扮演主機一方的協定。[`conformance/host.py`](conformance/host.py) 是測試卡帶執行所需的最少主機部分：工作 RAM、按 LoROM 解碼的卡帶、四個連接埠、垂直消隱旗標、乘法器與除法器、DMA，以及足以讀出畫面的視訊記憶體。它的處理器是 [mos65xx-python](https://github.com/gufranco/mos65xx-python) 的 65816，這個子模組只有 [`conformance/cartridges.py`](conformance/cartridges.py) 會匯入。兩者都不模擬此外的主機部分。

## 開機程式不在此處

這 64 個位元組屬於 Sony。本儲存庫不收錄、不下載它們，其中也沒有任何東西能重建它們。[`ssmp/artifacts.manifest.json`](ssmp/artifacts.manifest.json) 收錄了它們的四個摘要，不含任何位元組。以 SHA-256 為準；CRC32、MD5 和 SHA-1 用作交叉核對，SHA-256 相符但其中一項不符的檔案會以 `Corrupt` 拒絕。

搜尋次序為 `SSMP_BOOT_DIR`（可指定多個目錄），然後是本簽出旁邊的 `boot/`，然後是其內部的 `boot/`。每個型號以最先找到的副本為準。

## 型號

```python
import ssmp

for name, model in ssmp.MODELS.items():
    print(name, model.processor, model.memory, model.boot)

print(ssmp.Chip("S-SMP", boot=bytes(64)).model)
```

```
ssmp spc700 65536 64
ssmp
```

只有一個型號，因為 Sony 只推出了一個單元。目錄冊之所以存在，是為了讓日後發現的硬件差異成為一個新項目，而不是一個新介面。建立時仍須指定型號。若呼叫者在這裏習慣了省略它，便會對涵蓋十六款晶片的 mos65xx-python 寫出同樣的呼叫，得到一款沒有人選擇的晶片，因此不指定任何型號會引發錯誤，並列出所有現有型號。

## 它是否正確

目前不知道有任何關於 S-SMP 的 Sony 文件。Nintendo 的開發手冊 Book I 印出了控制暫存器和三個計時器，[`conformance/hardware.json`](conformance/hardware.json) 引用了這些頁面；`python3 -m conformance.quotes` 會在你放在 `docs/manufacturer/` 的副本中找到每條引文。其餘部分有三樣東西代替，全部位於[本系列權威階梯](FAMILY.md)的第二級：晶片本身的程式碼、附有在主機上實測數值的檢查，以及一個檢查卡帶。

**晶片本身的程式碼。** 開機程式是 Sony 編寫的 64 個位元組，因此主機介面是從中讀出的。[`conformance/console.py`](conformance/console.py) 把該序列記錄下來，[`conformance/boot.test.py`](conformance/boot.test.py) 則對單元重演：握手 `0xaa` 和 `0xbb`、目的地、一個每個位元組都以其自身計數確認的區塊、緊接第一個區塊的第二個區塊，以及跳轉至已上載內容。

**附有在主機上實測數值的檢查。** Shay Green，又名 blargg，編寫了三項以真實硬件衡量音效單元的檢查。`.spc` 檔案是把整個單元記錄下來，因此可以直接在此執行，中間不經任何主機：

| 檢查                   | 確定的內容                                                               | 子檢查 |       週期 |
| ---------------------- | ------------------------------------------------------------------------ | -----: | ---------: |
| `initial_regs.spc`     | 六個處理器暫存器、全部十六個非記憶體位址，以及聲音產生器的整個暫存器檔案 |      4 |    744,661 |
| `initial_in_ports.spc` | 四個連接埠，在程式最先執行時讀取                                         |      1 |    654,978 |
| `full_ram.spc`         | 每個記憶體位元組、堆疊頁、回聲緩衝區，以及堆疊指標下方的三個位元組       |      6 | 19,793,439 |

三項全部相符。[`conformance/hardware.json`](conformance/hardware.json) 記錄了每次執行。

**檢查卡帶，由精簡的主機驅動。** `python3 -m conformance.cartridges` 在該主機上執行它在 `SSMP_CARTRIDGE_DIR` 或 `cartridges/` 找到的每個測試卡帶，並把結果與逐一記錄它們的 [`conformance/cartridge.json`](conformance/cartridge.json) 比對。Shay Green 的 `spc_smp` 得出 18 項判定，全部 18 項相符，其中包括 `CPU/verify IPL ROM`、`CPU/smp reg read-write behavior`、三項隨機計時器檢查和 `CPU Timing/mem access times`。他的 `spc_dsp6` 就聲音產生器得出 104 項判定，全部 104 項相符；`spc_mem_access_times` 2 項中 2 項相符，`spc_timer` 1 項中 1 項相符。gilyon 的 `spctest` 測試除 `SLEEP` 和 `STOP` 以外的每個 SPC700 操作碼，報告 `Success`。Peter Lemon 的七個 SPC700 卡帶都在第一項檢查報告 `FAIL`，與預期只差一個位元：中斷旗標。這裏重設後它保持為設定狀態，[sony-spc700-python](https://github.com/gufranco/sony-spc700-python) 把它記錄為未解決的問題。Shay Green 那些檢查背後的計時器與暫存器修正記錄於 [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md)。沒有卡帶時它以 2 結束，並說明沒有執行任何東西；[`conformance/testroms.json`](conformance/testroms.json) 列出這個單元的每個測試卡帶，包括等待完整主機的那些。

`.spc` 檔案屬於 Shay Green，不收錄於此。[`conformance/checks.manifest.json`](conformance/checks.manifest.json) 以大小和四個摘要識別它們。請把你擁有的副本放在 `spc/`，或在 `SSMP_SPC_DIR` 中指定目錄；沒有它們時，`python3 -m conformance.against_checks` 以 2 結束，並說明沒有檢查任何東西。

凡資料來源與模型矛盾，或彼此矛盾，相關項目都記錄在 [`conformance/divergences.json`](conformance/divergences.json)。

## 參與開發

| 需要                                       | 位置                                                                  |
| :----------------------------------------- | :-------------------------------------------------------------------- |
| 每項關卡檢查及其執行次序                   | [CONTRIBUTING.md](CONTRIBUTING.md)                                    |
| 給編碼代理的同一份資料，以及容易出錯的地方 | [AGENTS.md](AGENTS.md)                                                |
| 本儲存庫與系列中其他儲存庫共用的標準       | [FAMILY.md](FAMILY.md)                                                |
| 尚未知道的事項，以及可確定每項的量度       | [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md)                                |
| 錯誤報告                                   | [GitHub Issues](https://github.com/gufranco/sony-s-smp-python/issues) |
| 安全報告                                   | [SECURITY.md](SECURITY.md)                                            |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 --with types-setuptools==84.0.0.20260812 mypy==1.14.1
cov=(uvx --python 3.12 --from coverage==7.6.10 --with setuptools==84.0.0 coverage)
"${cov[@]}" erase
for file in $(find ssmp conformance -name '*.test.py' | sort); do
  "${cov[@]}" run -a "$file"
done
"${cov[@]}" report
```

每個模組旁邊都有一個以其命名的測試檔案，各自可以獨立執行。覆蓋率是硬性關卡檢查，語句與分支均須達到 100%。凡需要開機程式或 Shay Green 檔案的檢查，都會跳過並說明原因，而不是報告通過。

`python3 -m conformance.against_checks` 和 `python3 -m conformance.speed` 在覆蓋率步驟之外執行。最長的檢查為 19,793,439 個週期，約為單元自身時間的 19 秒，而速度下限量度的是不帶追蹤器的模型。

## 參考資料

- _SNES Development Manual, Book I_，Nintendo of America Inc.，無日期。第 3 部分第 1、4、5 章。240 頁，21,022,582 個位元組，SHA-256 `f1405241000046abba7849376d2ec53cf85f1ad2e9950d69a7c2cf1f3ff6b791`。不可再分發，也不在本儲存庫內。
- S-SMP 開機程式，64 個位元組，SHA-256 `c95f88b299030d5afa55b1031e2b5ef2dff650c4b4e6bb6f8b1359436521278f`。屬於 Sony，不可再分發，也不在本儲存庫內。
- Shay Green，`initial_regs.spc`、`initial_in_ports.spc`、`full_ram.spc`，以及 `spc_smp`、`spc_dsp6`、`spc_mem_access_times` 和 `spc_timer` 卡帶，提供在主機上實測的數值；gilyon 的 `spctest` 和 Peter Lemon 的 SPC700 測試。全部不收錄於此。
- [SNESdev wiki, S-SMP](https://snes.nesdev.org/wiki/S-SMP)，是後來的文件而非 Sony 文件，在使用之處引用。
- [sony-spc700-python](https://github.com/gufranco/sony-spc700-python) 提供處理器，[sony-s-dsp-python](https://github.com/gufranco/sony-s-dsp-python) 提供聲音產生器，兩者各有其參考資料。聲音產生器以 Nintendo 自己的表格為標準。

## 引用本專案

[CITATION.cff](CITATION.cff) 會在每次發佈時，由寫入套件版本的腳本一併更新。

## 授權

MIT。見 [LICENSE](LICENSE)。
