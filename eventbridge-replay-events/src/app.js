exports.handler = async (event) => {
  const timeEventWasRaised = new Date(event.time);
  const timeToRaiseEvent = new Date();
  timeToRaiseEvent.setHours(timeEventWasRaised.getHours(), timeEventWasRaised.getMinutes(), timeEventWasRaised.getSeconds(), timeEventWasRaised.getMilliseconds());

  return {
    // original eventbridge event
    event,

    // new timestampt to raise event
    time: timeToRaiseEvent,

    // has the time alreaedy passed? If so don't process in state machine
    process: timeToRaiseEvent > new Date()
  };
};
