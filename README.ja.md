[English](README.md) | 日本語 | [简体中文](README.zh-Hans.md) | [繁體中文（香港）](README.zh-HK.md)

# Sony S-SMP

スーパーファミコンのSony S-SMPオーディオユニットをPythonで実装したものです。SPC700プロセッサとS-DSP音源が64 KB、4つのポート、3つのタイマー、64バイトのブートプログラムを共有します。このブートプログラムと、実機で採取した値を持つチェックに照らして検証しています。

[![CI](https://github.com/gufranco/sony-s-smp-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/sony-s-smp-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/sony-s-smp-python)](https://github.com/gufranco/sony-s-smp-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

本体とのインターフェースは**4**つのポートがすべてです。実機で採取した値を持つチェックが**3**つ、不一致は**0**件、チェックを集めたカートリッジによる判定**18**件のうち**14**件が一致、テストは**707**件、ステートメントとブランチのカバレッジは**100%**、依存関係はありません。

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

ユニットはブートプログラムを6,300サイクル実行し、その後ポート0で`0xaa`、ポート1で`0xbb`を返します。すべてのスーパーファミコンは、オーディオハードウェアに何かを送る前にこの2バイトを待ちます。続いて本体がポート0に`0xcc`を書き込むと、64サイクル後にブートプログラムがそれを返します。これはブロックを受け取る準備ができたことを意味します。

## インストール

| 要件 | バージョン |
|:--|:--|
| Python | 3.12以降 |
| git | 任意。2つのサブモジュールの取得に使います |
| ブートプログラム | すでにお持ちの64バイトのコピー |

```bash
git clone --recurse-submodules https://github.com/gufranco/sony-s-smp-python.git
cd sony-s-smp-python
python3 ssmp/doctor.py
```

パッケージは標準ライブラリ以外を何もインポートしません。プロセッサは[sony-spc700-python](https://github.com/gufranco/sony-spc700-python)、音源は[sony-s-dsp-python](https://github.com/gufranco/sony-s-dsp-python)で、どちらもサブモジュールとしてチェックアウトされます。これらがないと何もビルドできません。`git submodule update --init --recursive`で取得できます。

ブートプログラムはSonyのものであり、このリポジトリには含まれていません。コピーを`boot/`、このチェックアウトが置かれたディレクトリの`boot/`、または`SSMP_BOOT_DIR`で指定した任意のディレクトリに置いてください。ブートプログラムからユニットを構築する例は、それがないマシンでは実行を拒否し、何が足りないかを一文で示します。

ドクターはマシンとチェックアウトを確認し、ユニットを構築して、1行で終わります。パッケージに関するすべての結果が合格すれば0で、そうでなければ1で終了します。バグ報告には出力全体を貼り付けてください。両方のサブモジュールとブートプログラムがそろっていれば、次の行で終わります。

```
  5 checks, nothing to report
```

パッケージをインストールすると、同じレポートが`ssmp-doctor`としてもインストールされます。

リリースは[Semantic Versioning](https://semver.org/)に従い、semantic-releaseがコミット履歴から作成します。すべてのリリースにはタグが付き、[リリースページ](https://github.com/gufranco/sony-s-smp-python/releases)に掲載されます。

## インターフェース

`ssmp.Chip(model, boot=None, identity=None, images=None, fill=None)`は、電源が入りブートプログラムを実行中のユニットを1つ構築します。`model`は必須です。

| 引数 | 意味 |
|:--|:--|
| `model` | モデル名です。大文字と小文字、および区切り文字`-`、`_`、`.`と空白は無視されるため、`"S-SMP"`と`"s_smp"`はどちらも`ssmp`を構築します |
| `boot` | ブートプログラムの64バイトです。省略すると、ユニットはブートディレクトリを検索し、見つけたものをSHA-256で識別します |
| `identity` | 渡された`boot`の記録です。省略すると`supplied`として記録されます |
| `images` | ブートディレクトリの代わりに検索するカタログで、モデル名をキーとします |
| `fill` | 電源投入時にプロセッサのメモリを埋めるバイトです。省略するとランダムな値になります |

### 呼び出し

| 呼び出し | 効果 |
|:--|:--|
| `reset()` | 同じブートプログラムから、新しいプロセッサ、メモリ、音源、レジスタ空間を構築します。ユニットを返します |
| `step()` | プロセッサの1命令です。かかったサイクル数を返します |
| `run_for(cycles)` | 少なくとも`cycles`サイクルが経過するまで命令を実行します。費やしたサイクル数を返します |
| `read(index)` | 本体がポート`index`、0から3で読む値です。ユニットが最後にそこへ書き込んだバイトです |
| `write(index, value)` | 本体がポート`index`に書き込む値です。ユニットがそこで読むバイトです |

### 状態

| 属性 | 意味 |
|:--|:--|
| `model` | 正規のモデル名です |
| `part` | 同じ名前で、ブートカタログのキーとしての形です |
| `identity` | ブートプログラムの記録です。`part`、`processor`、`revision`、`bytes_long` |
| `cycles` | ユニットが構築されてからのプロセッサのサイクル数です。リセットではクリアされません |
| `processor` | プロセッササブモジュールのSPC700です |
| `dsp` | 音源サブモジュールのS-DSPです |
| `space` | プロセッサから見える64 KBで、16個のレジスタが`$00F0`に、ブートウィンドウが`$FFC0`にあります |

`processor`、`dsp`、`space`は、本体からは届かない部分に触れます。これらを操作するチェックは、部品ではなくモデルを検証しています。

### モジュールの内容

| 名前 | 内容 |
|:--|:--|
| `ssmp.MODELS` | 唯一の`Model`レコードで、名前をキーとします |
| `ssmp.Model` | `name`、`summary`、`processor`、`memory`、`boot`を持つレコードです |
| `ssmp.why_not()` | ここでユニットを構築できれば`None`、できなければ何が足りないかを示す一文です |
| `ssmp.available()` | ここで見つかったブートプログラムで、モデル名をキーとします |
| `ssmp.VERSION`、`ssmp.__version__` | インストールされているバージョンです |

| エラー | 発生する条件 |
|:--|:--|
| `ssmp.UnknownModelError` | モデルが指定されていないか、このパッケージが扱う名前ではない場合です。メッセージには存在する名前が列挙されます |
| `ssmp.NoBootRom` | サブモジュールがチェックアウトされていないか、そのモデルのブートプログラムが見つからない場合です |
| `ssmp.WrongShape` | ブートプログラムがちょうど64バイトではない場合です |
| `ssmp.Unrecognised` | ファイルのSHA-256が[`ssmp/artifacts.manifest.json`](ssmp/artifacts.manifest.json)のどれとも一致しない場合です |
| `ssmp.Corrupt` | ファイルがSHA-256では一致し、公開されている別のダイジェストでは一致しない場合、または記録済みの不良ダンプと一致する場合です |

```python
import ssmp
from ssmp import firmware

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
    firmware.identify(bytes(100))
except ssmp.Unrecognised as error:
    print(error)
```

```
no model was named, and this package will not choose one for you. Name one of: ssmp
s-dsp is not a unit this package covers; there is ssmp
a boot program is exactly 64 bytes and this one is 10
nothing in the manifest has sha256 cd00e292c5970d3c5e2f0ffa5171e555bc46bfc4faddfb4a418b6840b86e79a3. It is 100 bytes and a boot program is 64, so this is not one of them at all.
```

ファイルが正しいプログラムで形式だけが違う場合、メッセージは代わりに修正方法を示します。16進数のリストとして読む、またはより大きなファイルの先頭か末尾の64バイトを取る、といったものです。

### ポートは2バイト

```python
import ssmp

unit = ssmp.Chip("ssmp").reset()
unit.run_for(6300)
unit.write(2, 0x55)
print(unit.read(2), unit.space.read8(0xF6))
```

```
0 85
```

各ポートは、本体からユニットへの1バイトと、ユニットから本体への1バイトを保持します。本体はポート2に`0x55`を書き込み、0を読み返します。これはユニットが最後にそこへ書き込んだバイトです。一方、ユニットは`$F6`で85を読みます。ポートごとに1バイトしか持たないモデルは、2つの書き込みが交差するまではテストに通りますが、その時点でどちらも送っていない値を双方に渡してしまいます。

### タイマー

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

この例は64個のゼロバイトからユニットを構築するため、ブートプログラムのないマシンでも動作し、レジスタ空間を直接操作します。タイマー0と1はプロセッサの128サイクルごとに、タイマー2は16サイクルごとにティックします。各タイマーは、`$FA`から`$FC`の分周器に書き込まれた値でティックを分周し、分周値0は256で分周します。`$F1`の制御レジスタに`0x85`を書き込むと、タイマー0と2が有効になり、ブートウィンドウは見えたままになります。

タイマー0は98,304サイクルで3を数え、読み出しでカウンタがクリアされるため、2回目の読み出しでは0になります。タイマー2は20を数えて4を返します。カウンタが4ビットだからです。テストレジスタ、制御レジスタ、3つの分周器は書き込み専用で読み返されません。5つとも0を返します。

| アドレス | レジスタ |
|:--|:--|
| `$F0` | テスト。0を返します |
| `$F1` | 制御。ビット0から2でタイマー有効化、ビット4でポート0と1のクリア、ビット5でポート2と3のクリア、ビット7でブートウィンドウ。0を返します |
| `$F2`、`$F3` | 音源のアドレスとデータ |
| `$F4`から`$F7` | ポート0から3 |
| `$F8`、`$F9` | 通常のメモリ |
| `$FA`から`$FC` | タイマーの分周器。0を返します |
| `$FD`から`$FF` | タイマーのカウンタ。読み出しでクリアされます |

### コマンドラインツール

| コマンド | 内容 | 終了コード |
|:--|:--|:--|
| `python3 ssmp/doctor.py` | マシンとチェックアウトを報告し、ユニットを構築してリセットします | 0 報告事項なし、1 不合格の結果あり |
| `python3 -m conformance.against_checks` | Shay Greenの3つのチェックをユニットに対して実行します | 0 すべて一致、1 不一致またはダイジェストの不一致あり、2 何もチェックされなかった |
| `python3 -m conformance.speed` | 毎秒のプロセッササイクル数を、下限20,000に対して測定します | 0 下限以上、1 下限未満、2 何も測定されなかった |
| `python3 -m conformance.links` | このREADMEのすべてのアドレスを調べ、JSONレポートを出力します | 0 消えたものなし、1 404または410を返すものあり |
| `python3 -m conformance.package <wheel>` | ビルドされたwheelがすべてのモジュールを含み、テストを含まないことを確認します | 0 問題なし、1 問題ありまたはファイルが存在しない、2 wheelが指定されていない |

## 2つの半分を組み合わせて見つかったこと

どちらの半分も相手をモデル化していません。1本の配線を2つのモデルで表すことが、2つのモデルが食い違う原因になるからです。両者を組み合わせたことで、プロセッサの不具合が見つかりました。

プロセッサは、マニュアルに電源投入時の値が記載されていないことを理由に、リセット時にすべてのフラグをランダムにしていました。ブートプログラムは`mov $f4,#$aa`と`mov $f5,#$bb`で本体に応答しますが、これがポートに届くのはダイレクトページがゼロページのときだけです。ダイレクトページフラグがセットされていると、これらは`$01f4`の通常のメモリに書き込まれ、ハンドシェイクは現れず、どのカートリッジもオーディオプログラムをアップロードできません。修正は[sony-spc700-python](https://github.com/gufranco/sony-spc700-python)に入りました。このフラグはリセット後にクリアされます。

## ハードウェアで採取したチェックで見つかったこと

書き込み専用で読み返されない5つのレジスタが、その下にあるメモリの値を返していました。

`initial_regs.spc`は16個のレジスタすべてを順に読み、その結果のチェックサムを、作者が実機で採取した値と比較します。この5つのレジスタの値のあらゆる組み合わせのうち、チェックサムを再現するのはちょうど1つだけです。5つとも0を返す場合です。[SNESdev wiki](https://snes.nesdev.org/wiki/S-SMP)にも同じことが文章で書かれています。

その後、古い動作を元に戻して、チェックが失敗することを確認しました。サブチェック3で不一致となり、期待値`9d4d2100`に対して`d57e2579`を報告しました。他の2つのチェックは一致したままでした。どちらもこれらのレジスタを読まないためです。

## 箱に入った2つの半分ではなく、1つのユニット

プロセッサと音源は同じ64 KBを読みます。実際の部品でそうなっているからです。ボイスは圧縮されたブロックをそこから取り出し、エコーユニットはそこへ書き戻します。半分ごとに別のメモリを持たせると、プログラムがアップロードしたサンプルがすべて失われます。

音源はプロセッサの1サイクルごとに1クロックを受け取ります。[`ssmp/rates.py`](ssmp/rates.py)はこれを定数として書くのではなく導出しています。1つの水晶が、24の分周でプロセッサに届き、内部に32クロックを持つサンプルについて768の分周で音源に届きます。24かける32は768で、どちらも毎秒1,024,000になります。

```python
from ssmp import rates

print(rates.PROCESSOR_HZ, rates.GENERATOR_HZ, rates.GENERATOR_CLOCKS)
print(rates.SLOW_TIMER_CYCLES, rates.FAST_TIMER_CYCLES)
```

```
1024000 1024000 1
128 16
```

音源はランダムな状態ではなくリセットされた状態で起動します。これはこのユニットで唯一の例外です。本体のリセット線が音源に届いており、リセットされた音源はエコーを書き込みません。エコーレジスタがランダムだと、音源はその後上書きしてしまうメモリを指すことになります。

## モデル化していないもの

- **このユニットのクロックと本体のクロックの比率。** 両者は別々の水晶で動作し、どちらも他方を割り切らないため、比率は個々の基板の性質です。数値は公開しておらず、経過時間を本体のサイクル数で示すこともしていません。上記の比率は、1つの水晶上の2つの半分の間のものです。
- **プロセッサと音源。** それぞれが独立したメンバーで、ここではサブモジュールとして利用しています。
- **本体。** [`conformance/console.py`](conformance/console.py)はチェックの中で本体側のプロトコルを担うだけで、それ以外は何もモデル化していません。

## ブートプログラムはここにはありません

その64バイトはSonyのものです。このリポジトリはそれを含まず、ダウンロードもせず、リポジトリ内のどれもそれを再構成できません。[`ssmp/artifacts.manifest.json`](ssmp/artifacts.manifest.json)はそのダイジェストを4つ持ち、バイトは持ちません。判定はSHA-256で行います。CRC32、MD5、SHA-1は相互確認に使い、SHA-256で一致してそのいずれかで一致しないファイルは`Corrupt`として拒否されます。

検索順序は、複数のディレクトリを指定できる`SSMP_BOOT_DIR`、次にこのチェックアウトの隣の`boot/`、次にその中の`boot/`です。モデルごとに最初に見つかったコピーが使われます。

## モデル

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

Sonyが出荷したユニットは1つなので、モデルも1つです。カタログがあるのは、後からハードウェアの違いが見つかったときに、新しいインターフェースではなく新しいエントリーで済むようにするためです。それでも構築時にはモデル名を指定します。ここで省略することを覚えた呼び出し側は、16の部品を扱うmos65xx-pythonに対しても同じ呼び出しを書き、誰も選んでいない部品を受け取ることになります。そのため、何も指定しないと例外が発生し、存在するすべてのモデルが列挙されます。

## 正しいのか

S-SMPに関するSonyの文書は、存在が知られていません。その代わりとなるものが3つあり、いずれも[ファミリーの権威の階層](FAMILY.md)の2段目に位置します。チップ自身のコード、実機で採取した値を持つチェック、そしてチェックを集めたカートリッジです。

**部品自身のコード。** ブートプログラムはSonyが書いた64バイトなので、本体とのインターフェースはそこから読み取れます。[`conformance/console.py`](conformance/console.py)がその手順を書き起こし、[`conformance/boot.test.py`](conformance/boot.test.py)がそれをユニットに対して再生します。ハンドシェイクの`0xaa`と`0xbb`、転送先、各バイトがそれ自身のカウントで確認応答されるブロック、最初のブロックに続く2つ目のブロック、そしてアップロードされたものへのジャンプです。

**実機で採取した値を持つチェック。** blarggとして知られるShay Greenが、オーディオユニットを実機に照らして検証するチェックを3つ書きました。`.spc`ファイルはユニット全体を書き出したものなので、本体を介さずにここで直接実行できます。

| チェック | 確認する内容 | サブチェック | サイクル |
| --- | --- | ---: | ---: |
| `initial_regs.spc` | プロセッサの6つのレジスタ、メモリではない16個のアドレスすべて、音源のレジスタファイル全体 | 4 | 744,661 |
| `initial_in_ports.spc` | プログラムが最初に読む4つのポート | 1 | 654,978 |
| `full_ram.spc` | メモリの全バイト、スタックページ、エコーバッファ、スタックポインタの下の3バイト | 6 | 19,793,439 |

3つとも一致します。[`conformance/hardware.json`](conformance/hardware.json)に各実行が記録されています。

**簡略化した本体で動かす、チェックを集めたカートリッジ。** Shay Greenの`spc_smp`カートリッジは18件の判定に到達し、14件が一致します。1件ずつ[`conformance/cartridge.json`](conformance/cartridge.json)に記録しています。一致したものには`CPU/verify IPL ROM`と`CPU/smp reg read-write behavior`が含まれます。4件の不一致のうち3件はタイマーの進み方に関するもので、[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md)がすでに扱っている問題です。4件目の`CPU Timing/mem access times`は、プロセッサ側の問題として記録しています。

`.spc`ファイルはShay Greenのものであり、ここには含まれていません。[`conformance/checks.manifest.json`](conformance/checks.manifest.json)がサイズと4つのダイジェストでそれらを識別します。お持ちのコピーを`spc/`に置くか、`SSMP_SPC_DIR`でディレクトリを指定してください。ない場合、`python3 -m conformance.against_checks`は終了コード2で終了し、何もチェックされなかったことを示します。

情報源がモデルと、または情報源同士が矛盾する箇所は、[`conformance/divergences.json`](conformance/divergences.json)に記載しています。

## 開発にあたって

| 用途 | 場所 |
|:--|:--|
| すべてのゲートと実行順序 | [CONTRIBUTING.md](CONTRIBUTING.md) |
| コーディングエージェント向けの同じ内容と、つまずきやすい点 | [AGENTS.md](AGENTS.md) |
| このリポジトリがファミリーの他のリポジトリと共有する基準 | [FAMILY.md](FAMILY.md) |
| 未解明の事項と、それぞれを決着させる測定 | [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) |
| バグ報告 | [GitHub Issues](https://github.com/gufranco/sony-s-smp-python/issues) |
| セキュリティ報告 | [SECURITY.md](SECURITY.md) |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 mypy==1.14.1
python3 -m coverage erase
for file in $(find ssmp conformance -name '*.test.py' | sort); do
  python3 -m coverage run -a "$file"
done
python3 -m coverage report
```

各モジュールには、その名前にちなんだテストファイルが隣にあり、それぞれ単独で実行できます。カバレッジはステートメントとブランチで100%の必須ゲートです。ブートプログラムやShay Greenのファイルを必要とするチェックは、合格と報告するのではなく、スキップしてその旨を表示します。

`python3 -m conformance.against_checks`と`python3 -m conformance.speed`はカバレッジのステップの外で実行します。最も長いチェックは19,793,439サイクルで、ユニット自身の時間で約19秒です。また、速度の下限はトレーサーなしでモデルを測定します。

## 参考文献

- S-SMPのブートプログラム、64バイト、SHA-256 `c95f88b299030d5afa55b1031e2b5ef2dff650c4b4e6bb6f8b1359436521278f`。Sonyのものであり、再配布できず、このリポジトリにはありません。
- Shay Green、`initial_regs.spc`、`initial_in_ports.spc`、`full_ram.spc`、および`spc_smp`カートリッジ。実機で採取した値のため。ここには含まれていません。
- [SNESdev wiki, S-SMP](https://snes.nesdev.org/wiki/S-SMP)。Sonyの文書ではなく後年の文書で、使用箇所で引用しています。
- プロセッサについては[sony-spc700-python](https://github.com/gufranco/sony-spc700-python)、音源については[sony-s-dsp-python](https://github.com/gufranco/sony-s-dsp-python)。それぞれに独自の参考文献があります。音源はNintendo自身の表に照らして検証しています。

## 引用

[CITATION.cff](CITATION.cff)は、パッケージのバージョンを刻むスクリプトによってリリースごとに更新されます。

## ライセンス

MIT。[LICENSE](LICENSE)を参照してください。
