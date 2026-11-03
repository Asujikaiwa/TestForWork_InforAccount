# SplitBill frontend

Single-page Next.js 16 + TypeScript + Tailwind UI for the SplitBill API.
See the root `README.md` for the full setup; the API it talks to is described
in `../docs/API_CONTRACT.md`.

```bash
npm install
cp .env.example .env.local   # only needed if the backend is not on localhost:8000
npm run dev                  # http://localhost:3000
npm run check                # eslint + tsc + vitest
```

## Money handling

All amounts are integer **satang** inside the app (`src/lib/money.ts`).
User input is parsed from the string digit by digit (never `parseFloat`),
split calculations are integer arithmetic (`src/lib/split.ts`), and display
uses `Intl.NumberFormat("th-TH")` for the whole part with the two decimals
appended as text. So `0.1 + 0.2` is `10 + 20 = 30` satang and shows `0.30`,
and `100.00` split three ways shows `33.34 / 33.33 / 33.33`, the same
algorithm the backend uses (leftover satang go to members in the order listed,
which is the group's member order).
