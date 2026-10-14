'use strict';

/** Environment-based configuration. No secrets are defaulted. */

function required(name, fallback) {
  const value = process.env[name] ?? fallback;
  if (value === undefined || value === '') {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

function loadConfig(env = process.env) {
  return {
    port: Number(env.PORT ?? 5000),
    mongodbUri: env.MONGODB_URI ?? 'mongodb://localhost:27017/cinemind',
    // In test mode a throwaway default is fine; otherwise fail fast.
    jwtSecret: env.JWT_SECRET ?? (env.NODE_ENV === 'test' ? 'test-secret' : required('JWT_SECRET')),
    jwtExpiresIn: env.JWT_EXPIRES_IN ?? '7d',
    internalApiKey: env.INTERNAL_API_KEY ?? (env.NODE_ENV === 'test' ? 'test-internal-key' : required('INTERNAL_API_KEY')),
    moviesServiceUrl: (env.MOVIES_SERVICE_URL ?? 'http://localhost:8002').replace(/\/$/, ''),
    agentServiceUrl: (env.AGENT_SERVICE_URL ?? 'http://localhost:8001').replace(/\/$/, ''),
    agentTimeoutMs: Number(env.AGENT_TIMEOUT_MS ?? 45000),
    moviesTimeoutMs: Number(env.MOVIES_TIMEOUT_MS ?? 15000),
    nodeEnv: env.NODE_ENV ?? 'development',
  };
}

module.exports = { loadConfig };
