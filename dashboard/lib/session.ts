/**
 * SessionStore Interface & Implementation
 *
 * Supports:
 * - In-memory (development, Mac Phase 1)
 * - Redis (production)
 *
 * Session Format:
 * {
 *   session_id: string (HMAC-SHA256)
 *   user_id: number
 *   user_email: string
 *   csrf_token: string
 *   created_at: ISO-8601
 *   expires_at: ISO-8601
 * }
 */

export interface Session {
  session_id: string;
  user_id: number;
  user_email: string;
  csrf_token: string;
  created_at: string;
  expires_at: string;
}

export interface SessionStore {
  /**
   * Create a new session
   */
  create(session: Session): Promise<void>;

  /**
   * Retrieve a session by ID
   * Returns null if expired or not found
   */
  get(session_id: string): Promise<Session | null>;

  /**
   * Delete a session (logout)
   */
  delete(session_id: string): Promise<void>;

  /**
   * Delete all expired sessions (cleanup)
   */
  cleanupExpired(): Promise<void>;
}

/**
 * In-Memory Session Store (Development)
 *
 * Suitable for:
 * - Local development
 * - Single-process deployments (Mac Phase 1)
 *
 * WARNING: Sessions are lost on server restart
 */
class InMemorySessionStore implements SessionStore {
  private sessions: Map<string, Session> = new Map();

  async create(session: Session): Promise<void> {
    this.sessions.set(session.session_id, session);
    // Clean up immediately after adding to prevent unbounded growth
    this.cleanupExpired();
  }

  async get(session_id: string): Promise<Session | null> {
    const session = this.sessions.get(session_id);

    if (!session) {
      return null;
    }

    // Check if expired
    if (new Date(session.expires_at) < new Date()) {
      this.sessions.delete(session_id);
      return null;
    }

    return session;
  }

  async delete(session_id: string): Promise<void> {
    this.sessions.delete(session_id);
  }

  async cleanupExpired(): Promise<void> {
    const now = new Date();
    for (const [key, session] of this.sessions.entries()) {
      if (new Date(session.expires_at) < now) {
        this.sessions.delete(key);
      }
    }
  }
}

/**
 * Redis Session Store (Production)
 *
 * Suitable for:
 * - Multi-process deployments
 * - Distributed systems
 * - Session sharing across instances
 *
 * NOT IMPLEMENTED YET - placeholder for future
 */
class RedisSessionStore implements SessionStore {
  async create(session: Session): Promise<void> {
    throw new Error("Redis session store not yet implemented");
  }

  async get(session_id: string): Promise<Session | null> {
    throw new Error("Redis session store not yet implemented");
  }

  async delete(session_id: string): Promise<void> {
    throw new Error("Redis session store not yet implemented");
  }

  async cleanupExpired(): Promise<void> {
    throw new Error("Redis session store not yet implemented");
  }
}

/**
 * Factory: Create session store based on environment
 *
 * REDIS_URL set? → Redis store
 * Otherwise → In-memory store
 */
export function createSessionStore(): SessionStore {
  const redisUrl = process.env.REDIS_URL;

  if (redisUrl) {
    return new RedisSessionStore();
  }

  return new InMemorySessionStore();
}

// Singleton instance
let sessionStore: SessionStore | null = null;

/**
 * Get the configured session store
 */
export function getSessionStore(): SessionStore {
  if (!sessionStore) {
    sessionStore = createSessionStore();
  }
  return sessionStore;
}
