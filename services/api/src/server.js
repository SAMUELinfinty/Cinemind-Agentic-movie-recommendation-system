'use strict';

/* Entry point: connects MongoDB and listens on PORT (5000). */

require('dotenv').config();

const { loadConfig } = require('./config');

async function main() {
  const config = loadConfig();
  // eslint-disable-next-line global-require
  const mongoose = require('mongoose');
  const { createModels } = require('./models');
  const { createStores } = require('./stores');
  const { createApp } = require('./app');

  await mongoose.connect(config.mongodbUri);
  const models = createModels(mongoose);
  const stores = createStores(models);
  const app = createApp({ ...stores, config });

  app.listen(config.port, () => {
    console.log(`cinemind-api listening on :${config.port}`);
  });
}

if (require.main === module) {
  main().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}

module.exports = { main };
