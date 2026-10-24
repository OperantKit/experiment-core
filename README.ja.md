# experiment-core

:gb: [English README](README.md)

experiment-core は、強化スケジュールのまわりにセッションを組み立てます。セッションを始め、反応ごとにスケジュールを進め、強化子を提示しているあいだはセッションを待たせ、終了条件を満たしたらセッションを終え、そのすべてを型の決まったイベントとして記録します。実験文脈と、ABA・AAB・ABC のリニューアルの実験計画のモデルも持ちます。[OperantKit](https://github.com/OperantKit) の中では、スケジュールエンジン [contingency-py](https://github.com/OperantKit/contingency-py) と、セッションを動かす・記録するパッケージ（[session-runner](https://github.com/OperantKit/session-runner)、[session-recorder](https://github.com/OperantKit/session-recorder)）のあいだに位置します。

- **強化子の提示には時間がかかります。** セッションは開始イベントとともに強化中の状態に入り、終了イベントとともにそこを出ます。提示中の反応ではスケジュールは進みません。
- **終了条件**（強化子の回数、または制限時間）を更新のたびに確かめます。
- **イベントはすべて素のデータです。** ファイルに書く、表示器に送る、テストで確かめる、のいずれにも使えます。

AI のコーディングエージェント向けの案内は [AGENTS.md](AGENTS.md) にあります。

## インストール

Python 3.11 以上が必要です。experiment-core はまだ PyPI に登録されていません。本体と、必要な 2 つのパッケージを、依存の解決をせずに GitHub から入れます。

```bash
G=git+https://github.com/OperantKit
pip install --no-deps $G/contingency-dsl-py $G/contingency-py $G/experiment-core
```

`pip check` はこれらの開発版のあいだの版の不一致を報告しますが、以下の例には影響しません。

## 例

[contingency-dsl](https://github.com/OperantKit/contingency-dsl) の式を組み立て、強化子 2 回で終わるセッションとして動かし、イベントの記録を読みます。

```python
from contingency_dsl import parse
from contingency import from_dsl
from experiment_core import ReinforcementCountExit, Session, SessionState, StateChangeEvent

session = Session(from_dsl(parse("FR 3")), exit_condition=ReinforcementCountExit(count=2))
session.start(0.0)
responses = 0
for t in range(1, 11):  # 1 秒に 1 反応
    if session.state is SessionState.REINFORCING:
        session.end_reinforcement(float(t))  # 1 秒間の強化子への接近が終わる
        continue
    responses += 1
    session.update(float(t), responses)

print(session.state.name, session.reinforcement_count)  # FINISHED 2
print([(type(e).__name__, e.timestamp) for e in session.events if not isinstance(e, StateChangeEvent)])
# [('ReinforcerStartEvent', 3.0), ('ReinforcerEndEvent', 4.0),
#  ('ReinforcerStartEvent', 7.0), ('ReinforcerEndEvent', 8.0)]
```

同じイベントを、起きたそばからファイルや実時間の表示器に送るには、[session-runner](https://github.com/OperantKit/session-runner) でセッションを動かします。

## 含まれるもの

| モジュール | 役目 | 公開する名前 |
|---|---|---|
| `session` | セッション本体。状態 IDLE → RUNNING → REINFORCING → FINISHED、イベントの記録、並立スケジュールでのオペランダムごとの反応数（`handle_response_on(index, timestamp)`）、強化率、強化率を感度の指数で累乗した行動モメンタム（Nevin, 1992） | `Session` |
| `delay` | 遅延した強化子の効力 `exp(-k * delay)`。遅延に信号があるときは `k` を小さくします。各 `ReinforcerStartEvent` に記録されます | `DelayFunction` |
| `exit_condition` | セッションをいつ終えるか | `ExitCondition`、`ReinforcementCountExit`、`TimeLimitExit` |
| `events` | セッションの状態とイベント | `SessionState`、`ResponseEvent`、`ReinforcerStartEvent`、`ReinforcerEndEvent`、`StateChangeEvent`、`SessionEvent` |
| `sink` | `emit(event)` を持つものなら何でもイベントを受け取れます。`event_to_dict` は JSON にできる dict を返します | `EventSink`、`InMemorySink`、`event_to_dict` |
| `context` | 実験文脈。背景刺激を名前つきの特徴の強さで表し、コサイン類似度で比べます | `ExperimentContext` |
| `renewal` | ABA・AAB・ABC のリニューアルの実験計画（Bouton & Bolles, 1979; Bouton, 2004） | `RenewalParadigm`、`ContextualSession`、`RenewalExperiment`、`PhaseRecord`、`PhaseResult`、`renewal_index` |
| `clock` | シミュレーション用の仮想の時計と、実時間の時計 | `Clock`、`VirtualClock`、`RealtimeClock` |
| `observation` | スケジュールの判定に渡すセッションの状態のスナップショット（反応数、直前の強化子からの時間） | `Observation` |
| `protocols` | スケジュールのインタフェース。`contingency.Schedule` の別名です | `Schedule` |

experiment-core はスケジュールを実装しません（contingency-py が持ちます）。ログファイルも書きません（session-recorder）。ハードウェアともやりとりしません（[experiment-io](https://github.com/OperantKit/experiment-io)）。

## 制限

- まだ PyPI に登録されておらず、API は変わることがあります。
- `renewal_index` と `RenewalExperiment.predict_renewal` は、文脈の特徴ベクトルの類似度だけから `sim(test, acquisition) - sim(test, extinction)` として計算します。実験計画のモデルであって、反応のデータから計算する指標ではありません。
- ファイルに書いた実験プロトコルを読み込む機能はありません。セッションは Python で組み立てます。
- スケジュールに渡す時刻は減ってはいけません。1 つの `Session` は 1 個体の 1 セッションに使います。

## 開発

```bash
git clone https://github.com/OperantKit/experiment-core && cd experiment-core
python -m venv .venv
G=git+https://github.com/OperantKit
.venv/bin/python -m pip install --no-deps $G/contingency-dsl-py $G/contingency-py -e .
.venv/bin/python -m pip install pytest pytest-cov
.venv/bin/pytest
```

## 参考文献

- Bouton, M. E. (2004). Context and behavioral processes in extinction. *Learning & Memory*, 11(5), 485–494. https://doi.org/10.1101/lm.78804
- Bouton, M. E., & Bolles, R. C. (1979). Contextual control of the extinction of conditioned fear. *Learning and Motivation*, 10(4), 445–466. https://doi.org/10.1016/0023-9690(79)90057-2
- Nevin, J. A. (1992). An integrative model for the study of behavioral momentum. *Journal of the Experimental Analysis of Behavior*, 57(3), 301–316. https://doi.org/10.1901/jeab.1992.57-301

## ライセンス

MIT です。[LICENSE](LICENSE) を参照してください。
