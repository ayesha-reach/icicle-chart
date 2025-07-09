const crypto = require('crypto');
const tokenStore = require('../utils/tokenStore');

exports.generateToken = (req, res) => {
  const apiKey = req.headers['x-api-key'];
  if (apiKey !== process.env.ICICLE_API_KEY)
    return res.status(401).json({ error: 'Invalid API key' });

  const { customer_id } = req.body;
  if (!customer_id)
    return res.status(400).json({ error: 'customer_id is required' });

  const token = crypto.randomBytes(32).toString('hex');
  tokenStore.set(token, {
    customer_id,
    created_at: Date.now(),
    expires_at: Date.now() + 3600000,
  });

  const streamlitUrl = `${process.env.STREAMLIT_URL}?token=${token}&customer-id=${customer_id}`;
  res.json({ token, url: streamlitUrl, expires_in: 3600 });
};

exports.validateToken = (req, res) => {
  const apiKey = req.headers['x-api-key'];
  if (apiKey !== process.env.ICICLE_API_KEY)
    return res.status(401).json({ error: 'Invalid API key' });

  const { token } = req.body;
  const tokenData = tokenStore.get(token);
  if (!tokenData || Date.now() > tokenData.expires_at) {
    tokenStore.delete(token);
    return res.status(401).json({ error: 'Invalid or expired token' });
  }

  res.json({ valid: true, customer_id: tokenData.customer_id });
};

exports.cleanupTokens = (req, res) => {
  const apiKey = req.headers['x-api-key'];
  if (apiKey !== process.env.ICICLE_API_KEY)
    return res.status(401).json({ error: 'Invalid API key' });

  let removed = 0;
  for (const [key, val] of tokenStore.entries()) {
    if (Date.now() > val.expires_at) {
      tokenStore.delete(key);
      removed++;
    }
  }

  res.json({ message: 'Cleanup complete', removed, remaining: tokenStore.size });
};
