// Backend Bet type
export interface Bet {
  id: number;
  user_id: number;
  title: string;
  amount: number;  // Total matched stake
  criteria: string;
  status: 'active' | 'won' | 'lost' | 'cancelled';
  created_at: string;
  updated_at: string | null;
  username?: string;
  deadline: string;
  challenges?: Challenge[];
}

export interface Challenge {
  id: number;
  bet_id: number;
  challenger_id: number;
  challenger_username: string;
  amount: number;
  status: 'pending' | 'accepted' | 'rejected';
  created_at: string;
}

export interface User {
  id: number;
  email: string;
  username: string;
  points: number;
}
