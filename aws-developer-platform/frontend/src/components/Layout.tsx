import { AppBar, Box, Button, Container, Toolbar, Typography } from '@mui/material';
import { NavLink, Outlet } from 'react-router';

export function Layout(): React.JSX.Element {
  return (
    <Box>
      <AppBar position="static">
        <Toolbar sx={{ gap: 2 }}>
          <Typography variant="h6" component="h1" sx={{ flexGrow: 1 }}>
            AWS Developer Platform
          </Typography>
          <Button color="inherit" component={NavLink} to="/dashboard">Dashboard</Button>
          <Button color="inherit" component={NavLink} to="/requests/new">New request</Button>
          <Button color="inherit" component={NavLink} to="/approvals">Approvals</Button>
          <Button color="inherit" component={NavLink} to="/projects">Projects</Button>
        </Toolbar>
      </AppBar>
      <Container component="main" sx={{ py: 4 }}><Outlet /></Container>
    </Box>
  );
}
