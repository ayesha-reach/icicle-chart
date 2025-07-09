const express = require('express');
const router = express.Router();
const { generateToken, validateToken, cleanupTokens } = require('../controllers/tokenController');

router.post('/generate-token', generateToken);
router.post('/validate-token', validateToken);
router.post('/cleanup-tokens', cleanupTokens);

module.exports = router;
