import React, { useEffect, useState } from 'react'
import {
    Table,
    TableCell,
    TableBody,
    TableHead,
    TableRow,
    CheckboxField,
    Button, SelectField, Flex
  } from '@aws-amplify/ui-react';


const testData = [
    { "id": "123", "name": "Where is test", "missed": 1, "update_at": null, "createdAt": "2022-03-25T16:25:08.312Z", "updatedAt": "2022-03-25T16:25:08.312Z", "isChecked": false},
    { "id": "321", "name": "Where is test2", "missed": 2, "update_at": null, "createdAt": "2022-03-25T16:25:08.312Z", "updatedAt": "2022-03-25T16:25:08.312Z", "isChecked": false}
]


  // MAIN FUNCTION
  function CustomTable({data=testData, callBack}) {
    const [tableData, setTableData] = useState(testData)
    const [dropdownSelected, setDropdownSelected] = useState('')
    const [btnDisabled, setBtnDisabled] = useState(true)

    useEffect(() => {
      // eslint-disable-next-line
        data = data!= null ? data.map(i => { return {...i, isChecked: false} }) : testData
        setTableData(data)
    }, [data])

    // Controlled Check/Selected
    const setChecked = (e) => {
        const {name, checked} = e.target
        console.log('Checked:', name, checked)
        // FindIndex && Update rowData as checked
        const objIndex = tableData.findIndex(i => i.id === name)
        const newObj = [...tableData]
        newObj[objIndex].isChecked = checked
        // console.log('New Obj', newObj)
        setTableData(newObj)

        // Are any boxes checked???
        const checkedBoxes = newObj.findIndex(i => i.isChecked === true)
        setBtnDisabled(checkedBoxes === -1 ? true : false)
    }

    // Build Row Data
    const BuildRow = ({obj}) => {
      // console.log('BUILD ROW:', obj)
      if (obj.length < 1) return  null
      return obj.map(i => {
          const {id, name, order_status, cust_location, products, taskToken, isChecked} = i
              return (
                  <TableRow key={id}>
                      <CheckboxField
                          id={id}
                          key={id}
                          name={id}
                          value={true}
                          checked={isChecked}
                          onChange={(e) => setChecked(e)}
                      />
                      <TableCell>{id}</TableCell>
                      <TableCell>{name}</TableCell>
                      <TableCell>{cust_location}</TableCell>
                      <TableCell>{order_status}</TableCell>
                      <TableCell maxWidth={'10vw'}>{products}</TableCell>
                      <TableCell fontSize={'40px'} textAlign={'center'} >{taskToken != '' ? '🪙' : ''}</TableCell>
                  </TableRow>
              )
      })
    }


    // On Submit
    const _onClickBtn = (action) => {
        const filterCheckedRow = tableData.filter(i => i.isChecked === true)
        const selectedRows = filterCheckedRow.map(i => { return {id:i.id, taskToken:i.taskToken}})
        const pick_status = dropdownSelected === 'true'
        callBack({action, data:{selectedRows, pick_status}})
    }


    // Main Return
    return (
        <div style={{margin:'1em'}}>
        <Table
        highlightOnHover={true}
        size='default'
        variation='striped'
      >
        <TableHead>
          <TableRow>
            <TableCell as="th"></TableCell>
            <TableCell as="th">ID</TableCell>
            <TableCell as="th">Customer</TableCell>
            <TableCell as="th">Location</TableCell>
            <TableCell as="th">Status</TableCell>
            <TableCell as="th">Products</TableCell>
            <TableCell as="th">TaskToken</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          <BuildRow obj={tableData} />
        </TableBody>
      </Table>
      <Flex
        justifyContent="center"
        alignItems="flex-end"
      >
        <SelectField
            style={{width:'30vw'}} 
            placeholder="Select Delivery Status"
            value={dropdownSelected}
            onChange={(e) => setDropdownSelected(e.target.value)}
        >
            <option value={true}>Complete</option>
            {/* <option value={false}>Out of Stock</option> */}
        </SelectField>
        <Button
            style={{width:'25vw', height:'3em'}}
            size="small"
            disabled={btnDisabled || dropdownSelected === ''}
            onClick={() => _onClickBtn('add')}
        >Submit</Button>
      </Flex>
      </div>
    )
  }

  export default CustomTable