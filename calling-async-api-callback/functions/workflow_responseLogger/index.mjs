export const handler = async (event) => {
  
  const response = {
    statusCode: 200,
    body: JSON.stringify(event),
  };
  console.log(response);
  return response;
};
