# Sony S-SMP

用 Python 实现的 Super Nintendo 的 Sony S-SMP 音频单元：一个 SPC700 处理器和一个 S-DSP 声音发生器，共享 64 KB 内存、四个端口、三个定时器和一段 64 字节的引导程序。它以这段引导程序为准，并以在主机上取值的检查程序为准。

[English](README.md) | [日本語](README.ja.md) | 简体中文 | [繁體中文（香港）](README.zh-HK.md)

[![CI](https://github.com/gufranco/sony-s-smp-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/sony-s-smp-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/sony-s-smp-python)](https://github.com/gufranco/sony-s-smp-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**4** 个端口构成全部主机接口，**3** 个检查程序带有在主机上取得的值，**0** 处不一致，一盘检查卡带的 **18** 个判定全部一致，**900** 个测试，**100%** 语句和分支覆盖率，无依赖

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

该单元运行引导程序 6,300 个周期，之后在端口 0 上应答 `0xaa`，在端口 1 上应答 `0xbb`。每台 Super Nintendo 都要等到这两个字节，才会向音频硬件发送任何内容。随后主机向端口 0 写入 `0xcc`，64 个周期后引导程序将其回显，表示它已准备好接收一个数据块。

## 安装

| 要求     | 版本                         |
| :------- | :--------------------------- |
| Python   | 3.12 或更高                  |
| git      | 任意版本，用于获取两个子模块 |
| 引导程序 | 一份你已拥有的 64 字节副本   |

```bash
git clone --recurse-submodules https://github.com/gufranco/sony-s-smp-python.git
cd sony-s-smp-python
python3 ssmp/doctor.py
```

本包只导入标准库中的内容。处理器是 [sony-spc700-python](https://github.com/gufranco/sony-spc700-python)，声音发生器是 [sony-s-dsp-python](https://github.com/gufranco/sony-s-dsp-python)，两者都以子模块形式检出。没有它们则无法构建，`git submodule update --init --recursive` 可以获取它们。

引导程序属于 Sony，不在本仓库中。请把一份副本放在 `boot/` 中、放在本检出所在目录的 `boot/` 中，或放在 `SSMP_BOOT_DIR` 指定的任意目录中。在没有副本的机器上，每个用它构建单元的示例都会拒绝运行，并用一句话说明缺少什么。

诊断脚本检查机器和检出内容，构建单元，最后输出一行结果。关于本包的每项检查结果都通过时退出码为 0，否则为 1。提交缺陷报告时请粘贴它的全部输出。两个子模块和引导程序都存在时，它以如下内容结束：

```
  5 checks, nothing to report
```

安装本包时也会以 `ssmp-doctor` 的形式安装同一份报告。

版本发布遵循 [Semantic Versioning](https://semver.org/)，由 semantic-release 根据提交历史生成。每个版本都打了标签，并列在[发布页面](https://github.com/gufranco/sony-s-smp-python/releases)上。

## 接口

`ssmp.Chip(model, boot=None, identity=None, images=None, fill=None, seed=None)` 构建一个处于刚上电状态的单元：处理器、声音发生器、内存、十六个寄存器、端口、定时器以及驱动定时器的预分频器都由同一个种子生成随机状态，什么都不清零，在调用 `reset()` 之前什么都不运行。`model` 为必填参数。

| 参数       | 含义                                                                                                     |
| :--------- | :------------------------------------------------------------------------------------------------------- |
| `model`    | 型号名称。忽略大小写以及分隔符 `-`、`_`、`.` 和空格，因此 `"S-SMP"` 和 `"s_smp"` 都会构建 `ssmp`         |
| `boot`     | 一段引导程序的 64 字节。省略时，单元会搜索引导目录，并按 SHA-256 识别找到的文件                          |
| `identity` | 所提供 `boot` 的记录。省略时记录为 `supplied`                                                            |
| `images`   | 用于代替引导目录进行搜索的目录表，以型号名称为键                                                         |
| `fill`     | 上电时填充处理器内存的字节。省略时为随机值                                                               |
| `seed`     | 生成全部随机状态的种子。省略时为处理器的 `UNSET_SEED`，即 `0x5A5A5A5A`。同一个种子每次都构建出同一个单元 |

### 调用

| 调用                  | 效果                                                                                                                                                                                                                         |
| :-------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `reset()`             | 即主机的复位线。显示引导程序窗口，然后复位声音发生器和处理器，处理器随即开始运行引导程序。按 Nintendo 的 Book I 所载，停止全部三个定时器。内存、定时器的分频值、级数和计数器、预分频器、端口和其他寄存器保持原值。返回该单元 |
| `step()`              | 执行一条处理器指令。返回所用周期数                                                                                                                                                                                           |
| `run_for(cycles)`     | 执行指令，直到至少经过 `cycles` 个周期。返回实际消耗的周期数                                                                                                                                                                 |
| `read(index)`         | 主机在端口 `index`（0 到 3）读到的值：单元最后写入该端口的字节                                                                                                                                                               |
| `write(index, value)` | 主机向端口 `index` 写入的值：单元在该端口读到的字节                                                                                                                                                                          |

### 状态

| 属性        | 含义                                                              |
| :---------- | :---------------------------------------------------------------- |
| `model`     | 规范型号名称                                                      |
| `part`      | 同一名称，采用引导目录表的键名形式                                |
| `identity`  | 引导程序的记录：`part`、`processor`、`revision`、`bytes_long`     |
| `cycles`    | 自单元构建以来的处理器周期数。复位不会清零                        |
| `processor` | 来自处理器子模块的 SPC700                                         |
| `dsp`       | 来自声音发生器子模块的 S-DSP                                      |
| `space`     | 处理器所见的 64 KB，16 个寄存器位于 `$00F0`，引导窗口位于 `$FFC0` |

`processor`、`dsp` 和 `space` 能触及主机触及不到的部分。驱动它们的检查检验的是模型，而不是芯片本身。

### 模块内容

| 名称                                        | 内容                                                                                                                                                                                                 |
| :------------------------------------------ | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ssmp.MODELS`                               | 唯一的 `Model` 记录，以名称为键                                                                                                                                                                      |
| `ssmp.Model`                                | 包含 `name`、`summary`、`processor`、`memory` 和 `boot` 的记录                                                                                                                                       |
| `ssmp.why_not(held=None)`                   | 可以在本机构建单元时为 `None`，否则为说明缺少什么的一句话。`held` 是用来代替搜索进行判断的目录，形状与 `available()` 的返回值相同                                                                    |
| `ssmp.available(held=None, catalogue=None)` | 在本机找到的引导程序，以型号名称为键。给出 `held` 时不搜索，原样返回。`catalogue` 是与 [`ssmp/artifacts.manifest.json`](ssmp/artifacts.manifest.json) 形状相同的清单，用来代替本包自带的清单识别文件 |
| `ssmp.identify(image, catalogue=None)`      | 引导程序字节的记录，带有 `part`、`processor`、`revision` 和 `bytes_long`。会抛出 `Unrecognised` 或 `Corrupt`，有修复办法时会指出。`catalogue` 与 `available()` 相同                                  |
| `ssmp.VERSION`、`ssmp.__version__`          | 已安装的版本                                                                                                                                                                                         |

| 错误                     | 抛出时机                                                                                              |
| :----------------------- | :---------------------------------------------------------------------------------------------------- |
| `ssmp.UnknownModelError` | 未指定型号，或该名称不在本包覆盖范围内。消息会列出现有的名称                                          |
| `ssmp.NoBootRom`         | 某个子模块未检出，或找不到该型号的引导程序                                                            |
| `ssmp.WrongShape`        | 引导程序不是恰好 64 字节                                                                              |
| `ssmp.Unrecognised`      | 文件的 SHA-256 与 [`ssmp/artifacts.manifest.json`](ssmp/artifacts.manifest.json) 中的任何条目都不匹配 |
| `ssmp.Corrupt`           | 文件的 SHA-256 匹配，但另一个公开摘要不一致，或与已记录的坏转储匹配                                   |

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

当文件是正确的程序但形式不对时，消息会改为说明修复方法：按十六进制列表读取，或取较大文件的前 64 字节或后 64 字节。

### 一个端口是两个字节

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

每个端口保存一个从主机发往单元的字节，以及一个从单元发往主机的字节。主机向端口 2 写入 `0x55`，读回的是 200，这是上电时留在那里的值，因为引导程序从不写端口 2，而单元在 `$F6` 读到 85。每个端口只保存一个字节的模型在两次写入交错之前都能通过，一旦交错，就会给双方一个谁都没有发送过的值。

### 定时器

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

该示例用 64 个零字节构建单元，因此可以在没有引导程序的机器上运行，并直接驱动寄存器空间。定时器 0 和 1 每 128 个处理器周期计一个节拍，定时器 2 每 16 个周期计一个节拍。每个定时器把节拍数除以写入 `$FA` 到 `$FC` 处分频器的值，分频值为 0 时按 256 分频。向 `$F1` 处的控制寄存器写入 `0x85` 会启用定时器 0 和 2，并保持引导窗口可见。

定时器 0 在 98,304 个周期内计数到 3，读取会清零其计数器，因此第二次读取得到 0。定时器 2 计数 20 次，读出 4，因为计数器只有四位。测试寄存器、控制寄存器和三个分频器只写不读回：五个都返回 0。对这十六个寄存器的每次写入也会落到其下方的内存中，声音发生器直接读取那片内存。

| 地址           | 寄存器                                                                                            |
| :------------- | :------------------------------------------------------------------------------------------------ |
| `$F0`          | 测试。读出 0                                                                                      |
| `$F1`          | 控制：位 0 到 2 为定时器启用，位 4 清除端口 0 和 1，位 5 清除端口 2 和 3，位 7 为引导窗口。读出 0 |
| `$F2`、`$F3`   | 声音发生器的地址和数据                                                                            |
| `$F4` 到 `$F7` | 端口 0 到 3                                                                                       |
| `$F8`、`$F9`   | 备用寄存器。无论其下方内存保存什么，都读回最后写入的字节                                          |
| `$FA` 到 `$FC` | 定时器分频器。读出 0                                                                              |
| `$FD` 到 `$FF` | 定时器计数器，读取时清零                                                                          |

### 命令行工具

| 命令                                     | 作用                                          | 退出码                                                       |
| :--------------------------------------- | :-------------------------------------------- | :----------------------------------------------------------- |
| `python3 ssmp/doctor.py`                 | 报告机器和检出内容，然后构建并复位单元        | 0 无问题，1 有检查项未通过                                   |
| `python3 -m conformance.against_checks`  | 对单元运行 Shay Green 的三个检查程序          | 0 全部一致，1 有一个不一致或与其摘要不匹配，2 未检查任何内容 |
| `python3 -m conformance.speed`           | 测量每秒处理器周期数，下限为 20,000           | 0 达到或超过下限，1 低于下限，2 未测量任何内容               |
| `python3 -m conformance.quotes`          | 在记录所引用的手册中找出记录引用的每一句话    | 0 全部引文都找到，或本机没有手册；1 其他情况                 |
| `python3 -m conformance.links`           | 探测本 README 中的每个地址并输出 JSON 报告    | 0 没有失效，1 有一个返回 404 或 410                          |
| `python3 -m conformance.package <wheel>` | 检查构建好的 wheel 是否包含每个模块且不含测试 | 0 正常，1 有问题或文件不存在，2 未指定 wheel                 |

## 组合两半时发现的问题

两半都不为对方建模，因为同一根线有两个模型，正是两个模型产生分歧的根源。把它们组合起来，发现了处理器中的一个缺陷。

处理器在复位时把每个标志都设为随机值，理由是其手册没有给出上电值。引导程序用 `mov $f4,#$aa` 和 `mov $f5,#$bb` 应答主机，而这两条指令只有在直接页为零页时才会写到端口。直接页标志置位时，它们写入的是 `$01f4` 处的普通内存，握手永远不会出现，任何卡带都无法上传其音频程序。修复已提交到 [sony-spc700-python](https://github.com/gufranco/sony-spc700-python)：该标志在复位后为清零状态。

## 在硬件上取值的检查发现的问题

那五个只写不读回的寄存器，原先返回的是其下方的内存内容。

`initial_regs.spc` 按顺序读取全部十六个寄存器，并把结果的校验和与作者在主机上取得的值进行比较。在这五个寄存器的所有取值组合中，恰好只有一种能重现该校验和：五个都返回 0。[SNESdev wiki](https://snes.nesdev.org/wiki/S-SMP) 用文字说明了同样的结论。

之后又把旧行为放回去，观察检查失败的情形。它在子检查 3 上出现不一致，报告 `d57e2579`，而期望值是 `9d4d2100`。另外两个检查仍然一致，因为它们都不读取这些寄存器。

## 一个单元，而不是装在一个盒子里的两半

处理器和声音发生器读取同一块 64 KB 内存，因为在实际芯片上就是如此。各声部从中取出压缩数据块，回声单元又写回其中。每一半各用一份存储，就会丢失程序上传的每个采样。

处理器每走一个周期，声音发生器就走一个时钟。[`ssmp/rates.py`](ssmp/rates.py) 推导出这一点，而不是直接给出：同一个晶振经由除数 24 到达处理器，经由 768 到达声音发生器，每个采样内含 32 个时钟。24 乘以 32 等于 768，两者都得出每秒 1,024,000。

```python
from ssmp import rates

print(rates.PROCESSOR_HZ, rates.GENERATOR_HZ, rates.GENERATOR_CLOCKS)
print(rates.SLOW_TIMER_CYCLES, rates.FAST_TIMER_CYCLES)
```

```
1024000 1024000 1
128 16
```

构建单元时，声音发生器和处理器一样处于随机状态。主机的复位线同时连到两者，所以 `reset()` 会复位两者。处于复位状态的声音发生器不写回声。没有被复位的声音发生器照常接收时钟，如果它随机的标志寄存器开启了回声写入，它就会写到随机的回声寄存器所指向的地方。这一点被如实建模而不是被阻止，真实单元是否如此、怎样才能确定，见 [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md)。

## 未建模的内容

- **本单元时钟与主机时钟之间的任何比值。** 二者由各自的晶振驱动，彼此不能整除，因此比值只是某一块电路板的属性。这里不公布任何数值，也不提供以主机周期计的经过时间。上文的比值是同一晶振上两半之间的比值。
- **处理器和声音发生器。** 它们各自是独立的成员，在这里以子模块形式使用。
- **主机。** [`conformance/console.py`](conformance/console.py) 在检查中扮演主机一侧的协议。[`conformance/host.py`](conformance/host.py) 是测试卡带运行所需的最少主机部分：工作 RAM、按 LoROM 解码的卡带、四个端口、垂直消隐标志、乘法器和除法器、DMA，以及足以读出屏幕的视频内存。它的处理器是 [mos65xx-python](https://github.com/gufranco/mos65xx-python) 的 65816，这个子模块只有 [`conformance/cartridges.py`](conformance/cartridges.py) 会导入。两者都不建模除此之外的主机部分。

## 引导程序不在这里

这 64 个字节属于 Sony。本仓库不携带它们，不下载它们，其中也没有任何东西能重建它们。[`ssmp/artifacts.manifest.json`](ssmp/artifacts.manifest.json) 记录了它们的四个摘要，不含任何字节。SHA-256 起决定作用；CRC32、MD5 和 SHA-1 用于交叉核对，SHA-256 匹配但其中任一摘要不一致的文件会被作为 `Corrupt` 拒绝。

搜索顺序是 `SSMP_BOOT_DIR`（可以指定多个目录），然后是本检出旁边的 `boot/`，再然后是其中的 `boot/`。某个型号最先找到的副本生效。

## 型号

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

只有一个型号，因为 Sony 只出货了一种单元。目录表的存在，是为了让日后发现的硬件差异成为一个新条目，而不是一个新接口。构造时仍然要指定型号。调用者若在这里学会省略它，就会对覆盖十六种芯片的 mos65xx-python 写出同样的调用，并得到一个没人选择的芯片，所以不指定型号会抛出错误，并列出现有的每个型号。

## 它是否正确

目前不知道存在任何关于 S-SMP 的 Sony 文档。Nintendo 的开发手册 Book I 印出了控制寄存器和三个定时器，[`conformance/hardware.json`](conformance/hardware.json) 引用了这些页面；`python3 -m conformance.quotes` 会在你放在 `docs/manufacturer/` 中的副本里找到每条引文。其余部分有三样东西代替，都处于[本系列权威阶梯](FAMILY.md)的第二级：芯片自身的代码、带有在主机上取得的值的检查程序，以及一盘检查卡带。

**芯片自身的代码。** 引导程序是 Sony 编写的 64 个字节，因此主机接口直接从中读出。[`conformance/console.py`](conformance/console.py) 记下这一序列，[`conformance/boot.test.py`](conformance/boot.test.py) 对单元执行它：握手 `0xaa` 和 `0xbb`、目标地址、每个字节都用自身计数确认的一个数据块、第一个之后的第二个数据块，以及跳转到已上传的内容。

**带有在主机上取得的值的检查程序。** Shay Green（人称 blargg）编写了三个检查程序，用真实硬件来检验音频单元。`.spc` 文件就是记录下来的整个单元，因此它们可以在这里直接运行，中间不需要主机：

| 检查                   | 确定的内容                                                             | 子检查 |       周期 |
| ---------------------- | ---------------------------------------------------------------------- | -----: | ---------: |
| `initial_regs.spc`     | 六个处理器寄存器、全部十六个非内存地址，以及声音发生器的整个寄存器文件 |      4 |    744,661 |
| `initial_in_ports.spc` | 四个端口，在程序一开始就读取                                           |      1 |    654,978 |
| `full_ram.spc`         | 内存的每个字节、栈页、回声缓冲区，以及栈指针下方的三个字节             |      6 | 19,793,439 |

三个全部一致。[`conformance/hardware.json`](conformance/hardware.json) 记录了每次运行。

**检查卡带，由精简的主机驱动。** `python3 -m conformance.cartridges` 在该主机上运行它在 `SSMP_CARTRIDGE_DIR` 或 `cartridges/` 中找到的每盘测试卡带，并把结果与逐一记录它们的 [`conformance/cartridge.json`](conformance/cartridge.json) 比较。Shay Green 的 `spc_smp` 得出 18 个判定，全部 18 个一致，其中包括 `CPU/verify IPL ROM`、`CPU/smp reg read-write behavior`、三个随机定时器检查和 `CPU Timing/mem access times`。他的 `spc_dsp6` 关于声音发生器得出 104 个判定，全部 104 个一致；`spc_mem_access_times` 2 个中 2 个一致，`spc_timer` 1 个中 1 个一致。gilyon 的 `spctest` 测试除 `SLEEP` 和 `STOP` 以外的每个 SPC700 操作码，报告 `Success`。Peter Lemon 的七盘 SPC700 卡带都在第一个检查报告 `FAIL`，与期望只差一个位：中断标志。这里复位后它保持置位，[sony-spc700-python](https://github.com/gufranco/sony-spc700-python) 把它记录为未解决的问题。Shay Green 那些检查背后的定时器和寄存器修正记录在 [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) 中。没有卡带时它以 2 退出，并说明什么也没有运行；[`conformance/testroms.json`](conformance/testroms.json) 列出这个单元的每盘测试卡带，包括等待完整主机的那些。

`.spc` 文件属于 Shay Green，不在这里携带。[`conformance/checks.manifest.json`](conformance/checks.manifest.json) 用大小和四个摘要识别它们。请把你拥有的副本放在 `spc/` 中，或在 `SSMP_SPC_DIR` 中指定一个目录；没有它们时，`python3 -m conformance.against_checks` 以 2 退出，并说明未检查任何内容。

当资料与模型矛盾，或资料彼此矛盾时，相应条目记录在 [`conformance/divergences.json`](conformance/divergences.json) 中。

## 参与开发

| 需求                                   | 位置                                                                  |
| :------------------------------------- | :-------------------------------------------------------------------- |
| 每项门禁检查及其运行顺序               | [CONTRIBUTING.md](CONTRIBUTING.md)                                    |
| 面向编程代理的同一内容，以及容易踩的坑 | [AGENTS.md](AGENTS.md)                                                |
| 本仓库与本系列其他仓库共享的标准       | [FAMILY.md](FAMILY.md)                                                |
| 尚不知道的内容，以及能确定每一项的测量 | [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md)                                |
| 缺陷报告                               | [GitHub Issues](https://github.com/gufranco/sony-s-smp-python/issues) |
| 安全报告                               | [SECURITY.md](SECURITY.md)                                            |

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

每个模块旁边都有一个以其命名的测试文件，每个测试文件都可单独运行。覆盖率是硬性门禁检查，要求语句和分支覆盖率达到 100%。凡是需要引导程序或 Shay Green 某个文件的检查，都会跳过并说明原因，而不是报告通过。

`python3 -m conformance.against_checks` 和 `python3 -m conformance.speed` 在覆盖率步骤之外运行。最长的检查是 19,793,439 个周期，约合单元自身时间 19 秒，而速度下限测量的是不带跟踪器的模型。

## 参考资料

- _SNES Development Manual, Book I_，Nintendo of America Inc.，无日期。第 3 部分第 1、4、5 章。240 页，21,022,582 字节，SHA-256 `f1405241000046abba7849376d2ec53cf85f1ad2e9950d69a7c2cf1f3ff6b791`。不可再分发，不在本仓库中。
- S-SMP 引导程序，64 字节，SHA-256 `c95f88b299030d5afa55b1031e2b5ef2dff650c4b4e6bb6f8b1359436521278f`。属于 Sony，不可再分发，不在本仓库中。
- Shay Green，`initial_regs.spc`、`initial_in_ports.spc`、`full_ram.spc`，以及 `spc_smp`、`spc_dsp6`、`spc_mem_access_times` 和 `spc_timer` 卡带，提供在主机上取得的值；gilyon 的 `spctest` 和 Peter Lemon 的 SPC700 测试。都不在这里携带。
- [SNESdev wiki，S-SMP](https://snes.nesdev.org/wiki/S-SMP)，一份后来的文档，而非 Sony 文档，在用到之处引用。
- [sony-spc700-python](https://github.com/gufranco/sony-spc700-python) 提供处理器，[sony-s-dsp-python](https://github.com/gufranco/sony-s-dsp-python) 提供声音发生器，各自带有参考资料。声音发生器以 Nintendo 自己的表格为准。

## 引用本项目

[CITATION.cff](CITATION.cff) 在每次发布时由写入包版本号的脚本更新。

## 许可证

MIT。参见 [LICENSE](LICENSE)。
