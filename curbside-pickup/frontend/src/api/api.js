
const BASE_API_URI = process.env.REACT_APP_BASE_API_URI

function handleErrors(response) {
    if (!response.ok) {
        throw response
    }
    return response
}

export const Get = async (method) => {
    console.log('METHOD:', method)
    const url = `${BASE_API_URI}${method}`;
    return fetch(url, {
        method: 'GET',
        headers: {
            "Accept": "*/*",
            "Content-Type": "application/json"
        }
    })
        .then(handleErrors)
        .then(res => res.json())
        .catch(error => {
            const err = error.json()
            console.log(err.message)
            return err
        })
}

export const Post = async (method, data) => {
    console.log('METHOD:', method)
    const url = `${BASE_API_URI}${method}`;
    return fetch(url, {
        method: 'POST',
        headers: {
            "Accept": "*/*",
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    })
        .then(handleErrors)
        .then(res => res.json())
        .catch(error => {
            const err = error.json()
            console.log(err.message)
            return err
        })
}
