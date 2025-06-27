require('dotenv').config();

const express = require('express');
const tokenRoutes = require('./routes/tokenRoutes');

const app = express();
app.use(express.json());

app.use('/api', tokenRoutes); // e.g. /api/generate-token

app.listen(3000, () => console.log('Backend listening on :3000'));
