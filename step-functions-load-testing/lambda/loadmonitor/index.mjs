export const handler = function iterator(event, context, callback) {
    const { timer } = event;
    const { start = Date.now(), duration, targetConcurrency, rampUpDuration } = timer;
    const step = Math.round(targetConcurrency / rampUpDuration);
    let { currentConcurrency = step, stepTimer } = timer;

    if (stepTimer && Date.now() - stepTimer > 60000) {
        currentConcurrency += step;
        stepTimer = Date.now();
    } else if (!stepTimer) {
        stepTimer = Date.now();
    }

    callback(null, {
        timer: {
            start,
            duration,
            rampUpDuration,
            continue: start + (rampUpDuration || duration) * 60 * 1000 > Date.now(),
            targetConcurrency,
            currentConcurrency,
            stepTimer
        },
        items: Array(currentConcurrency || targetConcurrency).fill(1)
    });
};