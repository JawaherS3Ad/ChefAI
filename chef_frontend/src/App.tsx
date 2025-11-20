import { Route, Redirect, Switch } from 'wouter';
import { BottomNav } from './components/BottomNav';
import { GenerateHome } from './pages/GenerateHome';
import { PantryChef } from './pages/generate/PantryChef';
import { CreativeChef } from './pages/generate/CreativeChef';

const App = () => {
  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/20">
      <Switch>
        <Route path="/">
          <Redirect to="/generate" />
        </Route>
        <Route path="/generate" component={GenerateHome} />
        <Route path="/generate/pantry" component={PantryChef} />
        <Route path="/generate/creative" component={CreativeChef} />
      </Switch>

      <BottomNav />
    </div>
  );
};

export default App;
