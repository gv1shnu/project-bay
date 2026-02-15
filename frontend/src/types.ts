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
  status: string;          // "active" | "won" | "lost" | "cancelled"
  deadline: string;        // ISO date string for the bet deadline
  created_at: string;      // ISO date string
  username?: string;       // Creator's username (only present in public feed responses)
  challenges?: Challenge[]; // Challenges against this bet (only in public feed)
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
  status: string;               // "pending" | "accepted" | "rejected" | "cancelled"
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
