export default () => ({
  port: parseInt(process.env.PORT || '3000', 10),
  nodeEnv: process.env.NODE_ENV || 'development',
  
  database: {
    url: process.env.DATABASE_URL,
  },
  
  jwt: {
    secret: process.env.JWT_SECRET || 'your-super-secret-jwt-key',
    expiresIn: process.env.JWT_EXPIRATION || '24h',
  },
  
  cors: {
    origin: process.env.CORS_ORIGIN?.split(',') || ['http://localhost:3000', 'http://localhost:3001'],
  },
  
  websocket: {
    port: parseInt(process.env.WEBSOCKET_PORT || '3001', 10),
  },
  
  gpio: {
    relayPin: parseInt(process.env.GPIO_RELAY_PIN || '17', 10),
    simulated: process.env.GPIO_SIMULATED !== 'false',
  },
  
  ai: {
    pythonService: process.env.AI_SERVICE_URL || 'http://localhost:5000',
    personDetectionThreshold: parseFloat(process.env.PERSON_DETECTION_THRESHOLD || '0.5'),
  },
});
