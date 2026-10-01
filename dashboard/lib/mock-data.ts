/**
 * User-Specific Mock Data Generator
 *
 * Generates SmartBudget data based on user ID to simulate
 * per-user data instead of global mock data.
 *
 * In production: Replace with real database queries
 */

export interface IncomeSource {
  id: string;
  name: string;
  amount: number;
  frequency: "monthly" | "weekly" | "one-time";
  category: string;
}

export interface Expense {
  id: string;
  name: string;
  amount: number;
  category: string;
  date: string;
}

export interface BudgetCategory {
  id: string;
  name: string;
  allocated: number;
  spent: number;
}

export interface SmartBudgetData {
  userId: number;
  userEmail: string;
  month: string;
  incomeSources: IncomeSource[];
  expenses: Expense[];
  budgetCategories: BudgetCategory[];
  totalIncome: number;
  totalExpenses: number;
  netIncome: number;
}

/**
 * Generate deterministic but user-specific mock data
 * Uses user ID as seed for consistent data between requests
 */
function hashUserId(userId: number): number {
  let hash = 0;
  const str = `user_${userId}`;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash = hash & hash; // Convert to 32bit integer
  }
  return Math.abs(hash);
}

function getUserSpecificValue(userId: number, index: number, min: number, max: number): number {
  const seed = hashUserId(userId) + index;
  const random = Math.sin(seed) * 10000;
  const frac = random - Math.floor(random);
  return Math.floor(frac * (max - min) + min);
}

export function generateUserMockData(userId: number, userEmail: string): SmartBudgetData {
  const baseIncome = getUserSpecificValue(userId, 1, 3000, 8000);
  const today = new Date();
  const monthStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}`;

  // Income sources (2-4 per user)
  const incomeSourceCount = 2 + (hashUserId(userId) % 3);
  const incomeSources: IncomeSource[] = [];

  const incomeNames = ["Primary Job", "Freelance Work", "Passive Income", "Side Gig", "Consulting"];
  for (let i = 0; i < incomeSourceCount; i++) {
    const amount = getUserSpecificValue(userId, 100 + i, baseIncome * 0.3, baseIncome * 0.7);
    incomeSources.push({
      id: `income_${userId}_${i}`,
      name: incomeNames[i % incomeNames.length],
      amount,
      frequency: i === 0 ? "monthly" : i === 1 ? "weekly" : "one-time",
      category: "income",
    });
  }

  // Expenses (8-12 per user)
  const expenseCount = 8 + (hashUserId(userId) % 5);
  const expenses: Expense[] = [];
  const expenseCategories = ["Housing", "Food", "Transport", "Utilities", "Entertainment", "Healthcare"];
  const expenseNames = {
    Housing: ["Rent", "Mortgage", "Property Tax"],
    Food: ["Groceries", "Dining Out", "Coffee"],
    Transport: ["Gas", "Car Payment", "Transit"],
    Utilities: ["Electricity", "Water", "Internet"],
    Entertainment: ["Movies", "Games", "Hobbies"],
    Healthcare: ["Insurance", "Medical", "Gym"],
  };

  for (let i = 0; i < expenseCount; i++) {
    const category = expenseCategories[hashUserId(userId + i) % expenseCategories.length];
    const categoryNames = expenseNames[category as keyof typeof expenseNames];
    const name = categoryNames[i % categoryNames.length];
    const amount = getUserSpecificValue(userId, 200 + i, 20, 500);
    const daysAgo = getUserSpecificValue(userId, 300 + i, 0, 30);
    const date = new Date(today);
    date.setDate(date.getDate() - daysAgo);

    expenses.push({
      id: `expense_${userId}_${i}`,
      name,
      amount,
      category,
      date: date.toISOString().split("T")[0],
    });
  }

  // Budget categories
  const budgetCategories: BudgetCategory[] = [];
  for (const category of expenseCategories) {
    const categoryExpenses = expenses.filter((e) => e.category === category);
    const spent = categoryExpenses.reduce((sum, e) => sum + e.amount, 0);
    const allocated = spent + getUserSpecificValue(userId, 400 + expenseCategories.indexOf(category), 50, 300);

    budgetCategories.push({
      id: `budget_${userId}_${category}`,
      name: category,
      allocated,
      spent,
    });
  }

  const totalIncome = incomeSources.reduce((sum, s) => sum + s.amount, 0);
  const totalExpenses = expenses.reduce((sum, e) => sum + e.amount, 0);

  return {
    userId,
    userEmail,
    month: monthStr,
    incomeSources,
    expenses,
    budgetCategories,
    totalIncome,
    totalExpenses,
    netIncome: totalIncome - totalExpenses,
  };
}
