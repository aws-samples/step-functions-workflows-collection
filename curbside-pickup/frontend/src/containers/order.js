import React, { useEffect, useState } from 'react';
import { Button, Flex, Heading, TextField, TextAreaField, Loader, Card} from '@aws-amplify/ui-react';
import { v4 as uuidv4 } from 'uuid';
import {Post} from '../api/api'

const orderTemp = {
    id: "832e9980-d54e-46fa-b3ff-d95a00f0788b",
    name: "Enter Name",
    email: "customer_email@az.com",
    customer_id: "abc-123",
    store_id: "pdx-13-west",
    products: [
        {"sku": "sm-shirt-blu", "qty": 1},
        {"sku": "uni-hat-flag", "qty": 1}
    ]
}

function Order () {
    const [nameInput, setNameInput] = useState('')
    const [emailInput, setEmailInput] = useState('')
    const [locationInput, setLocationInput] = useState('')
    const [productInput, setProductInput] = useState('')
    const [isLoading, setIsLoading] = useState(false)

    useEffect(() => {
        // Do Something
        const {name, email, store_id, products} = orderTemp
        setNameInput(name)
        setEmailInput(email)
        setLocationInput(store_id)
        setProductInput(products)
    }, [])

    const handleSubmit = async () => {
        setIsLoading(true)
        // Construct Payload
        const payload = {
            id: uuidv4(),
            name: nameInput,
            email: emailInput,
            customer_id: `cust-${Math.floor(Math.random() * 100000)}`,
            store_id: locationInput,
            products: [
                {"sku": "sm-shirt-blu", "qty": 1},
                {"sku": "uni-hat-flag", "qty": 1}
            ]
        }
        const res = await Post('order', payload)
        console.log('POST RES:',res)
        setIsLoading(false)
        alert(JSON.stringify(res))
    }

    const onChangeNameInput = event => {
        setNameInput(event.target.value);
    };
    const onChangeEmailInput = event => {
        setEmailInput(event.target.value);
    };
    const onChangeLocationInput = event => {
        setLocationInput(event.target.value);
    };
    const onChangeProductInput = event => {
        setProductInput(event.target.value);
    };

    return (
        <>
            <Card>
                <Flex 
                    direction="column"
                    alignItems="center"
                >
                <Heading level={2} >Curbside Pickup Order</Heading>
                <Flex>
                    <TextField
                        label="Full Name"
                        onChange={onChangeNameInput}
                        value={nameInput}
                    />
                    <TextField
                        label="Email"
                        onChange={onChangeEmailInput}
                        value={emailInput}
                    />
                </Flex>
                <Flex>
                    <TextField
                        label="Store Location"
                        onChange={onChangeLocationInput}
                        value={locationInput}
                        width="38%"
                    />
                    <TextAreaField
                    label="Products"
                    onChange={onChangeProductInput}
                    value={JSON.stringify(productInput)}
                    rows="2"
                    width="60%"
                    isReadOnly={true}
                    />
                </Flex>
                <Button
                    loadingText=""
                    onClick={() => handleSubmit()}
                    ariaLabel=""
                    variation='primary'
                    width={'10em'}
                >
                    Submit
                </Button>
                </Flex>
                { isLoading ?
                <Loader style={{position:'fixed', zIndex:'999', overflow:'visible', margin:'auto', top:0, left:0, bottom:'33%', right:0}} 
                    width="6rem" height="6rem" 
                />
                : null
                }
            </Card>
        </>
    )
}

export default Order