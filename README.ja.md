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
- 刺激メタデータ（`contingency-annotator` にある）。
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
    (contingency, ext.)       (program → runtime)       (contingency-annotator)
```

Schedule インターフェースは `Protocol`（duck-typed）としてローカルに宣言されている。これにより本パッケージは具象スケジュール・ランタイム・パッケージへのハード依存なしにコンパイルとテストができる。`contingency-py` との統合は `apps/core/contingency-py/` に具象ランタイムが登場したときに行われる。

## インストール

```bash
mise exec -- python -m venv .venv
mise exec -- .venv/bin/python -m pip install -e '.[dev]'
```

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
| `protocols` | `Schedule`, `ConcurrentSchedule` |
| `clock` | `Clock`, `VirtualClock`, `RealtimeClock` |
| `sink` | `EventSink`, `InMemorySink`, `event_to_dict` |

明示的な非目標（他のパッケージか次の設計ラウンドに属するもの）:

- 実験プロトコル・ローダ (YAML/JSON → ランタイム・グラフ) と `ExperimentCore` ファサード — 上位のオーケストレータ・パッケージへ延期。v0 の `ExperimentCore` / `ExecutionEnvironmentAdapter` / `DataManager` 抽象化は **移植されていない**; これらは simulator 指向の v0 ワークフロー用のスキャフォールドで、ここで採用された Protocol 境界モデルに合わない。
- 永続化 / JSONL ロギング — `session-recorder` が `SessionEvent` を :class:`EventSink` 経由で消費する。
- 具象強化スケジュール — `contingency-py`（将来）が `Schedule` Protocol を実装する。
- 刺激 / 強化子メタデータ — `contingency-annotator`。
- ハードウェア I/O — `experiment-io`。

## 参考文献

- Bouton, M. E., & Bolles, R. C. (1979). Contextual control of the extinction of conditioned fear. *Learning and Motivation*, 10(4), 445–466. https://doi.org/10.1016/0023-9690(79)90057-2
- Bouton, M. E. (2004). Context and behavioral processes in extinction. *Learning & Memory*, 11(5), 485–494. https://doi.org/10.1101/lm.78804
- Nevin, J. A. (1992). An integrative model for the study of behavioral momentum. *Journal of the Experimental Analysis of Behavior*, 57(3), 301–316. https://doi.org/10.1901/jeab.1992.57-301
