import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Button, Flex, Heading, TextField, Loader, Card, SwitchField} from '@aws-amplify/ui-react';
import {Post} from '../api/api'


function Customer () {
    const [orderIdInput, setOrderId] = useState('')
    const [taskTokenInput, setTaskToken] = useState('')
    const [locationPosInput, setLocation] = useState('')
    const [isChecked, setIsChecked] = useState(false)
    const [isLoading, setIsLoading] = useState(false)

    const location = useLocation();

    useEffect(() => {
        // Do Something
        console.log(location);
        const qs = new URLSearchParams(location.search)
        setOrderId(qs.get('order'))
        setTaskToken(location.search.split('token=')[1])
    }, [location])

    const handleSubmit = async () => {
        setIsLoading(true)
        // Construct Payload
        const payload = {
            id: orderIdInput,
            taskToken: taskTokenInput,
            location: locationPosInput,
            taskComplete: !isChecked
        }
        const res = await Post('task-complete', payload)
        console.log('POST RES:',res)
        setIsLoading(false)
        alert(JSON.stringify(res))
    }

    const onChangeOrderInput = event => {
        setOrderId(event.target.value);
    };
    const onChangeTaskInput = event => {
        setTaskToken(event.target.value);
    };
    const onChangeLocation = event => {
        setLocation(event.target.value);
    };

    return (
        <>
            <Card>
                <Flex 
                    direction="column"
                    alignItems="center"
                >
                <Heading level={2} >Customer Submit Arrival</Heading>
                <TextField
                    label="Order ID"
                    onChange={onChangeOrderInput}
                    value={orderIdInput}
                    disabled={true}
                />
                <TextField
                    label="Task Token"
                    onChange={onChangeTaskInput}
                    value={taskTokenInput}
                    disabled={true}
                />
                <TextField
                    label="Parking Location"
                    onChange={onChangeLocation}
                    value={locationPosInput}
                />
                <SwitchField
                    label="Cancel Order"
                    isChecked={isChecked}
                    onChange={(e) => {
                    setIsChecked(e.target.checked);
                    }}
                />
                <Button
                    loadingText=""
                    onClick={() => handleSubmit()}
                    ariaLabel=""
                    variation='primary'
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

export default Customer