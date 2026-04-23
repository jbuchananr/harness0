### API Server to replace PII in place

We need 
1. statless light weight cache, maybe a redis that runs locally, or just in memory? 
2. Take text, apply PII, we might want to apply index on where we applied if possible, cache the values
3. take a different text with those PII values and then replace those values back

I would like to run this with open claw or a hermes agent