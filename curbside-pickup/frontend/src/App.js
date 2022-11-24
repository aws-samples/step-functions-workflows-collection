// import './App.css';
import { BrowserRouter as Router, Route, Routes} from "react-router-dom"
import { ThemeProvider } from '@aws-amplify/ui-react';
import '@aws-amplify/ui-react/styles.css'
import Order from './containers/order';
import Customer from './containers/customer-arrival';
import PickOrder from './containers/pick-order'
import DeliverOrder from './containers/curbside'
import Navbar from './components/navbar';


function App() {
  return (
    <Router>
      <ThemeProvider>
      <Navbar />
        <Routes>
          <Route path="/" element={<Order />} />
          <Route path="/arrival" element={ <Customer />} />
          <Route path="/pick-order" element={ <PickOrder />} />
          <Route path="/deliver" element={ <DeliverOrder />} />
        </Routes>
      </ThemeProvider>
    </Router>
  );
}

export default App;
