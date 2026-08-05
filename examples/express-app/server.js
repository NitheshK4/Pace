const express = require('express');
const { ResilientTelemetryQueue } = require('@pace-dev/sdk');

const app = express();
const paceQueue = new ResilientTelemetryQueue({
  apiKey: process.env.PACE_API_KEY || 'pace_demo_express_key',
  endpoint: process.env.PACE_ENDPOINT || 'http://localhost:8000'
});

app.use(express.json());

app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', service: 'express-example' });
});

app.listen(3000, () => {
  console.log('Express example listening on port 3000');
});
