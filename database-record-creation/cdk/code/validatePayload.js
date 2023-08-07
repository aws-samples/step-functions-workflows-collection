// create lambda function
const AWS = require('aws-sdk');
const { fields } = require('./businessRules.js');

exports.handler = async (event, context, callback) => {

    // for each field in the business rules, check if it exists in the event
    // and if rules are matching
    for (let i = 0; i < fields.length; i++) {

        // check if present
        if (!event[fields[i].name]) {
            callback(null, {
                statusCode: '200',
                body: {
                    'isValid': false,
                    'error': fields[i].name + ' is not present'
                }
            });
        }

        // check if required is present and not empty
        if (fields[i].required && !event[fields[i].name]) {
            callback(null, {
                statusCode: '200',
                body: {
                    'isValid': false,
                    'error': fields[i].name + ' is empty'
                }
            });
        }
    }

    // if all the above checks are passed, then return true
    callback(null, {
        statusCode: '200',
        body: {
            'isValid': true,
            ...event
        }
    });
}