# Contributing to CryptoBot Pro

We welcome contributions! Please read this guide before submitting a PR.

## Development Setup

```bash
git clone https://github.com/yourusername/crypto-trading-bot.git
cd crypto-trading-bot
cp .env.example .env
docker compose up --build
```

## Branching Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Production-ready code |
| `develop` | Integration branch |
| `feature/*` | New features |
| `fix/*` | Bug fixes |
| `chore/*` | Maintenance |

## Commit Convention (Conventional Commits)

```
feat: add MACD histogram divergence signal
fix: correct trailing stop calculation for short positions
docs: update backtest API documentation
chore: upgrade ccxt to 4.2.0
test: add RSI strategy edge case tests
refactor: extract order sizing into RiskManager
```

## Adding a New Strategy

1. Create a class in `backend/app/services/trading_engine.py` extending `BaseStrategy`
2. Implement `generate_signal(ctx: BotContext) -> Signal`
3. Register it in `STRATEGY_REGISTRY`
4. Add tests in `backend/tests/test_core.py`
5. Add to the frontend strategy dropdown in `BacktestPage.tsx` and `BotsPage.tsx`

```python
class MyStrategy(BaseStrategy):
    name = "my_strategy"
    default_params = {"period": 14}

    def generate_signal(self, ctx: BotContext) -> Signal:
        # Your logic here
        return Signal("hold", ctx.symbol, ctx.current_price, 0.0, "No signal")
```

## Code Quality

- Python: typed, async FastAPI patterns, PEP 8
- TypeScript: strict mode, functional React components
- No `any` types in TypeScript unless unavoidable
- All new endpoints need a docstring
- Run tests before opening a PR: `pytest backend/tests/ -v`

## Pull Request Checklist

- [ ] Tests pass locally
- [ ] No new linting errors
- [ ] Added/updated tests for changed code
- [ ] Updated relevant docs/README sections
- [ ] PR description explains what changed and why

## Reporting Bugs

Open a GitHub issue with:
- Steps to reproduce
- Expected vs actual behavior
- Backend version / environment
- Relevant log output

## License

By contributing, you agree your code will be licensed under MIT.
