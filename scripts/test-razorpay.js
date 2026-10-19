const response = await fetch("https://dhansetu-hub.onrender.com/api/payment/verify-live");
console.log(`payment verify status=${response.status}`);
console.log(await response.text());
process.exitCode = response.status === 200 ? 0 : 1;
