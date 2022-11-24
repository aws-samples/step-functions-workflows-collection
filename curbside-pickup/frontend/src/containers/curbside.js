import React, { useEffect, useState } from 'react';
import { Button, Flex, Heading, TextField, TextAreaField, Loader, Card} from '@aws-amplify/ui-react';
import {Get, Post} from '../api/api'
import Table from '../components/curbside-table'

function sleep(time) {
    return new Promise(resolve => setTimeout(resolve, time));
  }


function CurbsideDeliver () {
    const [fetchData, setFetchData] = useState(null)
    const [isLoading, setIsLoading] = useState(false)

    useEffect(() => {
        // Do Something
        _getData()
    }, [])


    const _getData = async () => {
        setIsLoading(true)
        // Call endpoint to get DynamoDb Data
        const res = await Get('ddb')
        setFetchData(res.Items.filter(item => item.order_status === 'customer-arrived'))
        console.log(res)
        setIsLoading(false)
    }

    const callbackTable = async ({action, data}) => {
        if (action === 'add') {
          setIsLoading(true)
          console.log('Submit Task Status true/false', data)
          const { selectedRows, pick_status } = data
          await Promise.all(selectedRows.map(async (i) => {
            const payload = {
                id: i.id,
                taskToken: i.taskToken,
                taskComplete: pick_status
            }
            const res = await Post('task-complete', payload)
            console.log('POST RES:',res)
          }));
            await sleep(400)
            _getData()
        }
      }


    return (
        <>
            <Card>
                <Flex 
                    direction="column"
                    alignItems="center"
                >
                <Heading level={2} >Curbside Deliver Order</Heading>
                
                </Flex>
                <Table data={fetchData} callBack={callbackTable}/>
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

export default CurbsideDeliver;