/**
 * types.ts — TypeScript interfaces for shared data structures.
 *
 * These mirror the backend Pydantic schemas and are used throughout
 * the frontend for type-safe API responses and component props.
 */

/**
 * Represents a bet (personal commitment) in the system.
 * Matches: backend schemas.BetWithUsername
 */
export interface Bet {
  id: number;
  user_id: number;
  title: string;           // The personal commitment (e.g., "I will run 5km")
  amount: number;          // Creator's total matched stake (grows when challenges are accepted)
  criteria: string;        // How success will be measured
  status: string;          //   'active' | 'pending' | 'won' | 'lost' | 'cancelled';
  stars: number;           // Number of stars (likes)
  deadline: string;        // ISO date string for the bet deadline
  proof_comment?: string;       // Creator's proof description
  proof_media_url?: string;     // URL to uploaded proof file
  proof_submitted_at?: string;  // ISO date string
  proof_deadline?: string;      // ISO date string — end of proof upload window
  created_at: string;      // ISO date string
  username?: string;       // Creator's username (only present in public feed responses)
  challenges?: Challenge[]; // Challenges against this bet (only in public feed)
  proof_votes?: ProofVote[]; // Votes on proof (only in public feed when proof_under_review)
  starred_by_user_ids?: number[]; // User IDs who starred this bet
}

/**
 * Represents a challenge against a bet.
 * A challenger stakes points betting the creator will fail.
 * Matches: backend schemas.ChallengeResponse
 */
export interface Challenge {
  id: number;
  bet_id: number;
  challenger_id: number;
  challenger_username: string;  // Resolved from User table
  amount: number;               // Points staked by the challenger
  status: 'won' | 'lost' | 'withdrew' | 'pending';
  created_at: string;
}

/** In-app notification (e.g. proof uploaded for a bet you challenged) */
export interface Notification {
  id: number;
  user_id: number;
  message: string;
  bet_id?: number;
  is_read: number;   // 0 = unread, 1 = read
  created_at: string;
}

/** A challenger's vote on uploaded proof */
export interface ProofVote {
  id: number;
  bet_id: number;
  user_id: number;
  username: string;  // Voter's username
  vote: string;      // "cool" or "not_cool"
  created_at: string;
}

/**
 * Represents a user's profile data.
 * Matches: backend schemas.UserResponse
 */
export interface User {
  id: number;
  email: string;
  username: string;
  points: number;   // In-app currency balance
  created_at?: string; // ISO date string (available in admin responses)
}
