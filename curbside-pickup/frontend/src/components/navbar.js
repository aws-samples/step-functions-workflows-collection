import { Link } from "react-router-dom";
import { Flex, SearchField, Image, Divider, Heading} from '@aws-amplify/ui-react';
import logo from '../assets/logo.png'


function Navbar() {

    return (
        <div>
            <Flex  style={{margin:'1em'}} height="2em" gap="3.5rem" alignItems='center'>
                {/* <Flex width='18%' alignItems='center'> */}
                    <Image height="2em" src={logo} />
                    <Heading marginLeft="-2em" level={4} fontWeight='bold'>State Machine</Heading>
                    <Link to="/" style={{ color:'#116a82', fontWeight:'bold', textDecoration: 'none' }} >Order</Link>
                    <Link to="/pick-order" style={{ color:'#116a82', fontWeight:'bold', textDecoration: 'none' }} >Pick Order</Link>
                    <Link to="/arrival" style={{ color:'#116a82', fontWeight:'bold', textDecoration: 'none' }} >Customer Arrival</Link>
                    <Link to="/deliver" style={{ color:'#116a82', fontWeight:'bold', textDecoration: 'none' }} >Curbside Deliver</Link>
            </Flex>
            <Divider orientation="horizontal" />
        </div>
    );
  }

  export default Navbar;