#!/usr/bin/env bash
cd /www/wwwroot/tools-cn.highkingflower.com
node -e 'const v=require("viem");console.log("base",!!v.base,"mainnet",!!v.mainnet,"arbitrum",!!v.arbitrum,"parseAbiItem",!!v.parseAbiItem,"createWalletClient",!!v.createWalletClient,"baseCa",!v.base);'
