/** Response shapes, see docs/API_CONTRACT.md. Money is always a string. */

export type Group = { id: number; name: string };

export type GroupDetail = Group & { members: string[] };

export type ExpenseShare = { member: string; amount: string };

export type Expense = {
  id: number;
  group_id: number;
  description: string;
  paid_by: string;
  amount: string;
  split_type: "equal" | "exact";
  shares: ExpenseShare[];
  created_by: string;
  created_at: string;
};

export type Balance = { member: string; balance: string };

export type BalancesResponse = { group_id: number; balances: Balance[] };

export type Split =
  | { type: "equal"; members: string[] }
  | { type: "exact"; shares: Record<string, string> };

export type NewExpense = {
  description: string;
  paid_by: string;
  amount: string;
  split: Split;
};

/** A recorded repayment: `from` paid `to` back. */
export type Payment = {
  id: number;
  group_id: number;
  from: string;
  to: string;
  amount: string;
  created_by: string;
  created_at: string;
};

export type NewPayment = { from: string; to: string; amount: string };

/** A suggested payment from GET /settle-up. */
export type Settlement = { from: string; to: string; amount: string };

export type SettleUpResponse = { group_id: number; payments: Settlement[] };

