# experiment-core

:gb: [English README](README.md)

operantkit のための実験オーケストレーション・コア。

## 役割

セッション・ライフサイクル管理、実験コンテキスト（Bouton の背景刺激）、再燃パラダイム (ABA/AAB/ABC)。本パッケージは宣言的な `contingency-dsl` プログラムをライブ・セッションに変換するランタイム・オーケストレータ: 強化子の供給タイミングを決定し、反応イベントを追跡し、コンテキスト依存のフェーズ遷移を管理する。

## 責務

- **Session**: ライフサイクル (IDLE → RUNNING → REINFORCING → FINISHED)、イベントログ、終了条件、並立（複数 operandum）サポート、強化遅延の効力計算。
- **ExperimentContext**: Bouton スタイルのコンテキスト刺激で、随伴性をゲートまたは変調する（背景手がかり、状況セット）。
- **Renewal**: ABA/AAB/ABC コンテキスト依存の回復パラダイム (Bouton & Bolles, 1979; Bouton, 2004)。
- **仮想クロック・フック**: 決定論的な時間源抽象化。シミュレーションがリアルタイム待機をしなくて済む。

## 責務外

- スケジュール・アルゴリズム自体（`contingency` / `contingency-py` にある）。
- 刺激メタデータ（`contingency-dsl-py` にある）。
- イベント永続化 / JSONL ロギング（`session-recorder` にある）。
- UI、ハードウェア・ブリッジ（`experiment-io`、`operantkit-frontend` にある）。

## アーキテクチャ

```
                         ┌──────────────────────────┐
                         │     experiment-core      │
                         │  ┌────────────────────┐  │
                         │  │ Session            │  │
                         │  │ ExperimentContext  │  │
                         │  │ Renewal            │  │
                         │  └─────────┬──────────┘  │
                         └────────────┼─────────────┘
                    依存 (Protocol 経由)
                                      │
                ┌─────────────────────┼──────────────────────┐
                ▼                     ▼                      ▼
    スケジュール・ランタイム   contingency-dsl-py AST    刺激メタデータ
    (contingency, ext.)       (program → runtime)       (contingency-dsl-py)
```

`experiment_core.Schedule` は `contingency.Schedule` の別名であり、本パッケージは独自のスケジュール・インターフェースを宣言しない。`Session` は `step(now, event)` と `reset()` でスケジュールを駆動する。並立スケジュールは `contingency.Concurrent` のインスタンスで、`components` のキーが各 operandum を表す。`Session.handle_response_on(index, timestamp)` は整数の operandum 番号を対応する component キーに対応づける。

## インストール

```bash
pip install experiment-core
```

開発用:

```bash
mise exec -- python -m venv .venv
mise exec -- .venv/bin/python -m pip install -e '.[dev]'
```

## 30 秒で動く例

[contingency-dsl](https://github.com/OperantKit/contingency-dsl) からスケジュールをコンパイルし、強化子 2 回で終わるセッションとして動かし、イベント記録を読む:

```python
from contingency_dsl import parse
from contingency import from_dsl
from experiment_core import ReinforcementCountExit, Session, SessionState, StateChangeEvent

session = Session(from_dsl(parse("FR 3")), exit_condition=ReinforcementCountExit(count=2))
session.start(0.0)
responses = 0
for t in range(1, 11):  # 1 秒に 1 反応
    if session.state is SessionState.REINFORCING:
        session.end_reinforcement(float(t))  # 1 秒間の強化子提示を終える
        continue
    responses += 1
    session.update(float(t), responses)

print(session.state.name, session.reinforcement_count)  # FINISHED 2
print([(type(e).__name__, e.timestamp) for e in session.events if not isinstance(e, StateChangeEvent)])
# [('ReinforcerStartEvent', 3.0), ('ReinforcerEndEvent', 4.0),
#  ('ReinforcerStartEvent', 7.0), ('ReinforcerEndEvent', 8.0)]
```

`contingency-py` と `contingency-dsl-py` は依存として一緒に入る。同じイベントをファイルやダッシュボードに送るには、[session-runner](https://github.com/OperantKit/session-runner)（`pip install session-runner`）でセッションを駆動する。

## 自作の 50 行のセッションループでは足りない理由

スケジュールに「強化か否か」だけを問うループは、セッションのデータが依存する次の点を落とす:

- **強化子の提示は区間である.** `Session` は `ReinforcerStartEvent` とともに `REINFORCING` に入り、`end_reinforcement` が呼ばれると `ReinforcerEndEvent` とともに出る。その間スケジュールは進めない。
- **終了条件.** `ReinforcementCountExit` と `TimeLimitExit` を更新のたびに検査し、`FINISHED` への `StateChangeEvent` でセッションを終える。
- **強化遅延.** 各 `ReinforcerStartEvent` は、きっかけとなった反応から提示までの遅延に基づく `potency` を記録する（`DelayFunction`、`exp(-k * delay)`。遅延中に信号があると `k` が小さくなる）。
- **並立スケジュールのオペランダム.** `handle_response_on(index, timestamp)` は反応を `Conc(...)` の 1 成分に渡し、オペランダムごとの反応数を保持する。
- **文脈と復活.** `ExperimentContext` は文脈をコサイン類似度で比較する。`RenewalExperiment` と `renewal_index` は ABA・AAB・ABC の復活の実験計画を扱う。
- **イベントはデータ.** すべてのイベントは dataclass で、`event_to_dict` で JSON にできる辞書になり、`emit(event)` を持つ任意のオブジェクトが受け取れる。

## 開発

```bash
.venv/bin/pytest
.venv/bin/pytest --cov=src --cov-report=term-missing
.venv/bin/ruff check src tests
.venv/bin/black src tests
```

## スコープ

本パッケージが所有するもの:

| モジュール | エクスポート |
|---|---|
| `session` | `Session` |
| `context` | `ExperimentContext` |
| `renewal` | `RenewalParadigm`, `ContextualSession`, `RenewalExperiment`, `PhaseRecord`, `PhaseResult`, `renewal_index` |
| `events` | `SessionState`, `ResponseEvent`, `ReinforcerStartEvent`, `ReinforcerEndEvent`, `StateChangeEvent`, `SessionEvent` |
| `exit_condition` | `ExitCondition`, `ReinforcementCountExit`, `TimeLimitExit` |
| `observation` | `Observation` |
| `delay` | `DelayFunction` |
| `protocols` | `Schedule`（`contingency.Schedule` の別名） |
| `clock` | `Clock`, `VirtualClock`, `RealtimeClock` |
| `sink` | `EventSink`, `InMemorySink`, `event_to_dict` |

明示的な非目標（他のパッケージか次の設計ラウンドに属するもの）:

- 実験プロトコル・ローダ (YAML/JSON → ランタイム・グラフ) と `ExperimentCore` ファサード — 上位のオーケストレータ・パッケージへ延期。v0 の `ExperimentCore` / `ExecutionEnvironmentAdapter` / `DataManager` 抽象化は **移植されていない**; これらは simulator 指向の v0 ワークフロー用のスキャフォールドで、ここで採用された Protocol 境界モデルに合わない。
- 永続化 / JSONL ロギング — `session-recorder` が `SessionEvent` を :class:`EventSink` 経由で消費する。
- 具象強化スケジュール — `contingency-py`（`contingency.ScheduleBuilder`）。
- 刺激 / 強化子メタデータ — `contingency-dsl-py`。
- ハードウェア I/O — `experiment-io`。

## 参考文献

- Bouton, M. E., & Bolles, R. C. (1979). Contextual control of the extinction of conditioned fear. *Learning and Motivation*, 10(4), 445–466. https://doi.org/10.1016/0023-9690(79)90057-2
- Bouton, M. E. (2004). Context and behavioral processes in extinction. *Learning & Memory*, 11(5), 485–494. https://doi.org/10.1101/lm.78804
- Nevin, J. A. (1992). An integrative model for the study of behavioral momentum. *Journal of the Experimental Analysis of Behavior*, 57(3), 301–316. https://doi.org/10.1901/jeab.1992.57-301
