import React, { useState, useEffect } from 'react';
import { 
  Users, Search, Mail, Building2, TicketIcon, Clock, 
  TrendingUp, AlertCircle, ChevronRight, X, ExternalLink,
  Filter, ArrowUpDown, Loader2
} from 'lucide-react';
import { useNavigate, useSearchParams } from 'react-router-dom';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const StatusBadge = ({ status }) => {
  const colors = {
    todo: 'bg-slate-500/20 text-slate-400',
    in_progress: 'bg-blue-500/20 text-blue-400',
    waiting: 'bg-amber-500/20 text-amber-400',
    review: 'bg-purple-500/20 text-purple-400',
    resolved: 'bg-emerald-500/20 text-emerald-400',
    closed: 'bg-gray-500/20 text-gray-400'
  };
  
  return (
    <span className={`text-[10px] px-2 py-0.5 rounded-full ${colors[status] || colors.todo}`}>
      {status?.replace('_', ' ')}
    </span>
  );
};

const PriorityBadge = ({ priority }) => {
  const colors = {
    urgent: 'bg-red-500/20 text-red-400',
    high: 'bg-orange-500/20 text-orange-400',
    medium: 'bg-yellow-500/20 text-yellow-400',
    low: 'bg-green-500/20 text-green-400'
  };
  
  return (
    <span className={`text-[10px] px-2 py-0.5 rounded-full ${colors[priority] || colors.medium}`}>
      {priority}
    </span>
  );
};

const CustomerDetailDrawer = ({ customer, onClose }) => {
  const navigate = useNavigate();
  
  if (!customer) return null;
  
  const { email, name, domain, company, stats, tickets } = customer;
  
  const handleTicketClick = (ticketId) => {
    navigate(`/all-tickets?ticket=${ticketId}`);
    onClose();
  };
  
  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Drawer */}
      <div className="relative w-full max-w-2xl bg-background border-l border-border shadow-2xl flex flex-col h-full animate-in slide-in-from-right duration-300">
        {/* Header */}
        <div className="p-6 border-b border-border bg-secondary/20">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-full bg-gradient-to-br from-primary/40 to-accent/40 flex items-center justify-center text-xl font-semibold text-white">
                {name?.charAt(0).toUpperCase() || email?.charAt(0).toUpperCase()}
              </div>
              <div>
                <h2 className="text-xl font-semibold">{name || email?.split('@')[0]}</h2>
                <p className="text-sm text-muted-foreground">{email}</p>
                {domain && (
                  <div className="flex items-center gap-1 mt-1 text-xs text-muted-foreground">
                    <Building2 size={12} />
                    <span>{company || domain}</span>
                  </div>
                )}
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-secondary/50 transition-colors"
            >
              <X size={20} />
            </button>
          </div>
        </div>
        
        {/* Stats Grid */}
        <div className="p-6 border-b border-border">
          <h3 className="text-sm font-medium text-muted-foreground mb-4">CUSTOMER METRICS</h3>
          <div className="grid grid-cols-4 gap-4">
            <div className="p-4 rounded-lg bg-secondary/30 border border-border/30">
              <div className="text-2xl font-bold text-primary">{stats?.total_tickets || 0}</div>
              <div className="text-xs text-muted-foreground">Total Tickets</div>
            </div>
            <div className="p-4 rounded-lg bg-secondary/30 border border-border/30">
              <div className="text-2xl font-bold text-amber-400">{stats?.open_tickets || 0}</div>
              <div className="text-xs text-muted-foreground">Open</div>
            </div>
            <div className="p-4 rounded-lg bg-secondary/30 border border-border/30">
              <div className="text-2xl font-bold text-emerald-400">{stats?.resolved_tickets || 0}</div>
              <div className="text-xs text-muted-foreground">Resolved</div>
            </div>
            <div className="p-4 rounded-lg bg-secondary/30 border border-border/30">
              <div className="text-2xl font-bold">
                {stats?.avg_resolution_hours ? `${stats.avg_resolution_hours}h` : '-'}
              </div>
              <div className="text-xs text-muted-foreground">Avg Resolution</div>
            </div>
          </div>
          
          {/* Priority & Status Breakdown */}
          <div className="mt-4 grid grid-cols-2 gap-4">
            {/* Priority Breakdown */}
            <div className="p-3 rounded-lg bg-secondary/20 border border-border/30">
              <div className="text-xs font-medium text-muted-foreground mb-2">By Priority</div>
              <div className="flex flex-wrap gap-2">
                {Object.entries(stats?.priority_breakdown || {}).map(([priority, count]) => (
                  count > 0 && (
                    <span key={priority} className="text-xs">
                      <PriorityBadge priority={priority} /> {count}
                    </span>
                  )
                ))}
              </div>
            </div>
            
            {/* Status Breakdown */}
            <div className="p-3 rounded-lg bg-secondary/20 border border-border/30">
              <div className="text-xs font-medium text-muted-foreground mb-2">By Status</div>
              <div className="flex flex-wrap gap-2">
                {Object.entries(stats?.status_breakdown || {}).map(([status, count]) => (
                  count > 0 && (
                    <span key={status} className="text-xs">
                      <StatusBadge status={status} /> {count}
                    </span>
                  )
                ))}
              </div>
            </div>
          </div>
          
          {/* Timeline */}
          <div className="mt-4 flex items-center gap-6 text-xs text-muted-foreground">
            <div className="flex items-center gap-1">
              <Clock size={12} />
              <span>First contact: {stats?.first_contact ? new Date(stats.first_contact).toLocaleDateString() : 'N/A'}</span>
            </div>
            <div className="flex items-center gap-1">
              <TrendingUp size={12} />
              <span>Last contact: {stats?.last_contact ? new Date(stats.last_contact).toLocaleDateString() : 'N/A'}</span>
            </div>
          </div>
        </div>
        
        {/* Tickets List */}
        <div className="flex-1 overflow-y-auto p-6">
          <h3 className="text-sm font-medium text-muted-foreground mb-4">
            RECENT TICKETS ({tickets?.length || 0})
          </h3>
          <div className="space-y-2">
            {tickets?.map(ticket => (
              <button
                key={ticket.ticket_id}
                onClick={() => handleTicketClick(ticket.ticket_id)}
                className="w-full p-3 rounded-lg bg-secondary/20 border border-border/30 hover:bg-secondary/40 transition-colors text-left group"
                data-testid={`customer-ticket-${ticket.ticket_id}`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono text-muted-foreground">{ticket.ticket_id}</span>
                      <PriorityBadge priority={ticket.priority} />
                      <StatusBadge status={ticket.status} />
                    </div>
                    <h4 className="font-medium mt-1 truncate">{ticket.title}</h4>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {new Date(ticket.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <ChevronRight size={16} className="text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
              </button>
            ))}
            
            {(!tickets || tickets.length === 0) && (
              <div className="text-center py-8 text-muted-foreground">
                No tickets found for this customer
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

const CustomersPage = ({ user }) => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('ticket_count');
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const [loadingCustomer, setLoadingCustomer] = useState(false);
  
  useEffect(() => {
    fetchCustomers();
  }, []);
  
  // Handle URL params for opening customer drawer
  useEffect(() => {
    const customerEmail = searchParams.get('customer');
    if (customerEmail) {
      loadCustomerDetail(customerEmail);
    }
  }, [searchParams]);
  
  const fetchCustomers = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/customers`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setCustomers(data);
      }
    } catch (error) {
      console.error('Failed to fetch customers:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const loadCustomerDetail = async (email) => {
    setLoadingCustomer(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/customers/${encodeURIComponent(email)}`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setSelectedCustomer(data);
      }
    } catch (error) {
      console.error('Failed to load customer detail:', error);
    } finally {
      setLoadingCustomer(false);
    }
  };
  
  const handleCustomerClick = (customer) => {
    setSearchParams({ customer: customer.email });
    loadCustomerDetail(customer.email);
  };
  
  const handleCloseDrawer = () => {
    setSelectedCustomer(null);
    setSearchParams({});
  };
  
  // Filter and sort customers
  const filteredCustomers = customers
    .filter(c => {
      if (!searchQuery) return true;
      const query = searchQuery.toLowerCase();
      return (
        c.email?.toLowerCase().includes(query) ||
        c.name?.toLowerCase().includes(query) ||
        c.domain?.toLowerCase().includes(query)
      );
    })
    .sort((a, b) => {
      if (sortBy === 'ticket_count') return (b.ticket_count || 0) - (a.ticket_count || 0);
      if (sortBy === 'last_ticket_date') {
        return new Date(b.last_ticket_date || 0) - new Date(a.last_ticket_date || 0);
      }
      if (sortBy === 'name') return (a.name || a.email).localeCompare(b.name || b.email);
      return 0;
    });
  
  return (
    <div className="p-6 space-y-6" data-testid="customers-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold flex items-center gap-3">
            <Users className="text-primary" />
            Customers
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            View and manage customer profiles and their ticket history
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <div className="px-4 py-2 rounded-lg bg-secondary/30 border border-border/30">
            <div className="text-2xl font-bold text-primary">{customers.length}</div>
            <div className="text-xs text-muted-foreground">Total Customers</div>
          </div>
        </div>
      </div>
      
      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-md">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by name, email, or domain..."
            className="w-full h-10 pl-10 pr-4 rounded-lg bg-secondary/30 border border-border/30 focus:outline-none focus:ring-2 focus:ring-primary/50"
            data-testid="customer-search-input"
          />
        </div>
        
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
          className="h-10 px-4 rounded-lg bg-secondary/30 border border-border/30 focus:outline-none focus:ring-2 focus:ring-primary/50"
          data-testid="customer-sort-select"
        >
          <option value="ticket_count">Most Tickets</option>
          <option value="last_ticket_date">Recent Activity</option>
          <option value="name">Name (A-Z)</option>
        </select>
      </div>
      
      {/* Customers Grid */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="animate-spin text-primary" size={32} />
        </div>
      ) : filteredCustomers.length === 0 ? (
        <div className="text-center py-20">
          <Users size={48} className="mx-auto text-muted-foreground/30 mb-4" />
          <h3 className="text-lg font-medium">No customers found</h3>
          <p className="text-sm text-muted-foreground mt-1">
            {searchQuery ? 'Try adjusting your search' : 'Customers will appear here when tickets are created'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredCustomers.map(customer => (
            <button
              key={customer.email}
              onClick={() => handleCustomerClick(customer)}
              className="p-4 rounded-xl bg-card border border-border/50 hover:border-primary/30 hover:shadow-lg transition-all text-left group"
              data-testid={`customer-card-${customer.email}`}
            >
              <div className="flex items-start gap-3">
                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-primary/30 to-accent/30 flex items-center justify-center text-lg font-semibold shrink-0">
                  {customer.name?.charAt(0).toUpperCase() || customer.email?.charAt(0).toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-medium truncate group-hover:text-primary transition-colors">
                    {customer.name || customer.email?.split('@')[0]}
                  </h3>
                  <p className="text-sm text-muted-foreground truncate">{customer.email}</p>
                  {customer.domain && (
                    <div className="flex items-center gap-1 mt-1 text-xs text-muted-foreground">
                      <Building2 size={10} />
                      <span>{customer.domain}</span>
                    </div>
                  )}
                </div>
              </div>
              
              <div className="mt-4 pt-3 border-t border-border/30 flex items-center justify-between">
                <div className="flex items-center gap-1 text-sm">
                  <TicketIcon size={14} className="text-primary" />
                  <span className="font-medium">{customer.ticket_count}</span>
                  <span className="text-muted-foreground text-xs">tickets</span>
                </div>
                <div className="text-xs text-muted-foreground">
                  {customer.last_ticket_date 
                    ? `Last: ${new Date(customer.last_ticket_date).toLocaleDateString()}`
                    : 'No activity'
                  }
                </div>
              </div>
            </button>
          ))}
        </div>
      )}
      
      {/* Customer Detail Drawer */}
      {(selectedCustomer || loadingCustomer) && (
        <>
          {loadingCustomer ? (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
              <Loader2 className="animate-spin text-primary" size={48} />
            </div>
          ) : (
            <CustomerDetailDrawer 
              customer={selectedCustomer} 
              onClose={handleCloseDrawer} 
            />
          )}
        </>
      )}
    </div>
  );
};

export default CustomersPage;
