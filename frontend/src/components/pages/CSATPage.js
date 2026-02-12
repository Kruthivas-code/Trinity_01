import React, { useState, useEffect } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { Star, CheckCircle2, Loader2, AlertCircle, MessageSquare, Send } from 'lucide-react';
import { TridentIcon } from '../common/TridentIcon';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const StarRating = ({ rating, onRate, interactive = true, size = 'lg' }) => {
  const [hovered, setHovered] = useState(0);
  
  const sizeClasses = {
    sm: 'w-6 h-6',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
    xl: 'w-16 h-16'
  };
  
  return (
    <div className="flex items-center gap-2">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          disabled={!interactive}
          onClick={() => interactive && onRate?.(star)}
          onMouseEnter={() => interactive && setHovered(star)}
          onMouseLeave={() => interactive && setHovered(0)}
          className={`transition-all duration-200 ${interactive ? 'cursor-pointer hover:scale-110' : 'cursor-default'}`}
        >
          <Star
            className={`${sizeClasses[size]} transition-colors ${
              star <= (hovered || rating)
                ? 'fill-yellow-400 text-yellow-400'
                : 'fill-transparent text-gray-300'
            }`}
          />
        </button>
      ))}
    </div>
  );
};

const CSATPage = () => {
  const { token } = useParams();
  const [searchParams] = useSearchParams();
  const initialRating = parseInt(searchParams.get('rating') || '0');
  
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [alreadySubmitted, setAlreadySubmitted] = useState(false);
  const [error, setError] = useState(null);
  const [rating, setRating] = useState(initialRating);
  const [responseId, setResponseId] = useState(null);
  const [ticketId, setTicketId] = useState(null);
  const [ticketTitle, setTicketTitle] = useState('');
  const [customerName, setCustomerName] = useState('');
  const [feedback, setFeedback] = useState('');
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  const [statusChecked, setStatusChecked] = useState(false);
  
  const ratingLabels = {
    1: 'Terrible',
    2: 'Poor',
    3: 'Okay',
    4: 'Good',
    5: 'Excellent'
  };
  
  // Check token status on page load (GET is safe for prefetch)
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const response = await fetch(`${BACKEND_URL}/api/csat/check/${token}`);
        const data = await response.json();
        
        if (!response.ok) {
          throw new Error(data.detail || 'Invalid survey link');
        }
        
        setTicketId(data.ticket_id);
        setTicketTitle(data.ticket_title);
        setCustomerName(data.customer_name);
        
        if (data.status === 'already_submitted') {
          setAlreadySubmitted(true);
          setRating(data.rating);
        } else {
          // Token is valid and not yet submitted - set initial rating from URL
          setRating(initialRating);
        }
        setStatusChecked(true);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    
    if (token) {
      checkStatus();
    } else {
      setError('No survey token provided');
      setLoading(false);
    }
  }, [token, initialRating]);
  
  const submitRating = async (ratingValue) => {
    setSubmitting(true);
    setError(null);
    
    try {
      // Use POST to prevent email client prefetch attacks
      const response = await fetch(`${BACKEND_URL}/api/csat/rate/${token}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rating: ratingValue })
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to submit rating');
      }
      
      if (data.already_submitted) {
        setAlreadySubmitted(true);
        setRating(data.rating);
        setTicketId(data.ticket_id);
      } else {
        setSubmitted(true);
        setRating(ratingValue);
        setResponseId(data.response_id);
        setTicketId(data.ticket_id);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };
  
  const submitFeedback = async () => {
    if (!feedback.trim() || !responseId) return;
    
    setSubmitting(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/csat/${responseId}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ feedback: feedback.trim() })
      });
      
      if (response.ok) {
        setFeedbackSubmitted(true);
      }
    } catch (err) {
      console.error('Failed to submit feedback:', err);
    } finally {
      setSubmitting(false);
    }
  };
  
  const handleRateClick = (ratingValue) => {
    setRating(ratingValue);
  };
  
  const handleConfirmRating = () => {
    if (rating >= 1 && rating <= 5) {
      submitRating(rating);
    }
  };
  
  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-primary mx-auto mb-4" />
          <p className="text-white/70">Loading survey...</p>
        </div>
      </div>
    );
  }
  
  // Error state
  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white/10 backdrop-blur-xl rounded-2xl p-8 text-center border border-white/10">
          <div className="w-16 h-16 rounded-full bg-red-500/20 flex items-center justify-center mx-auto mb-6">
            <AlertCircle className="w-8 h-8 text-red-400" />
          </div>
          <h1 className="text-2xl font-bold text-white mb-3">Oops!</h1>
          <p className="text-white/70 mb-6">{error}</p>
          <p className="text-white/50 text-sm">
            This survey link may have expired or is invalid.
          </p>
        </div>
      </div>
    );
  }
  
  // Already submitted state
  if (alreadySubmitted) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white/10 backdrop-blur-xl rounded-2xl p-8 text-center border border-white/10">
          <div className="flex justify-center mb-6">
            <TridentIcon className="w-12 h-12 text-primary" />
          </div>
          <h1 className="text-2xl font-bold text-white mb-3">Already Submitted</h1>
          <p className="text-white/70 mb-6">
            You&apos;ve already rated this ticket. Thank you for your feedback!
          </p>
          <div className="flex justify-center mb-4">
            <StarRating rating={rating} interactive={false} size="lg" />
          </div>
          <p className="text-white/50 text-sm">
            Your rating: {rating}/5 ({ratingLabels[rating]})
          </p>
          {ticketId && (
            <p className="text-white/40 text-xs mt-4">
              Ticket: #{ticketId}
            </p>
          )}
        </div>
      </div>
    );
  }
  
  // Success state - rating submitted
  if (submitted) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white/10 backdrop-blur-xl rounded-2xl p-8 border border-white/10">
          {/* Header */}
          <div className="text-center mb-8">
            <div className="w-16 h-16 rounded-full bg-emerald-500/20 flex items-center justify-center mx-auto mb-6">
              <CheckCircle2 className="w-8 h-8 text-emerald-400" />
            </div>
            <h1 className="text-2xl font-bold text-white mb-2">Thank You!</h1>
            <p className="text-white/70">Your feedback has been recorded</p>
          </div>
          
          {/* Rating display */}
          <div className="text-center mb-8 p-6 rounded-xl bg-white/5">
            <p className="text-white/60 text-sm mb-3">Your rating</p>
            <div className="flex justify-center mb-2">
              <StarRating rating={rating} interactive={false} size="lg" />
            </div>
            <p className="text-white font-medium text-lg">{ratingLabels[rating]}</p>
          </div>
          
          {/* Optional feedback */}
          {!feedbackSubmitted ? (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-white/70">
                <MessageSquare size={18} />
                <span className="text-sm font-medium">Any additional feedback? (Optional)</span>
              </div>
              <textarea
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                placeholder="Tell us more about your experience..."
                className="w-full h-24 px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder:text-white/30 focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none"
                data-testid="csat-feedback-input"
              />
              <button
                onClick={submitFeedback}
                disabled={!feedback.trim() || submitting}
                className="w-full py-3 rounded-xl bg-primary hover:bg-primary/90 text-white font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                data-testid="csat-submit-feedback"
              >
                {submitting ? (
                  <>
                    <Loader2 size={18} className="animate-spin" />
                    Submitting...
                  </>
                ) : (
                  <>
                    <Send size={18} />
                    Submit Feedback
                  </>
                )}
              </button>
              <p className="text-center text-white/40 text-xs">
                Skip this if you prefer not to share more details
              </p>
            </div>
          ) : (
            <div className="text-center p-6 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
              <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
              <p className="text-emerald-400 font-medium">Feedback submitted!</p>
              <p className="text-white/60 text-sm mt-1">We appreciate your detailed response.</p>
            </div>
          )}
          
          {/* Footer */}
          <div className="mt-8 pt-6 border-t border-white/10 text-center">
            <div className="flex justify-center mb-2">
              <TridentIcon className="w-6 h-6 text-primary/60" />
            </div>
            <p className="text-white/40 text-xs">
              Powered by Trinity Support
            </p>
            {ticketId && (
              <p className="text-white/30 text-xs mt-1">
                Ticket: #{ticketId}
              </p>
            )}
          </div>
        </div>
      </div>
    );
  }
  
  // Default state - show rating selection
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white/10 backdrop-blur-xl rounded-2xl p-8 text-center border border-white/10">
        <div className="flex justify-center mb-6">
          <TridentIcon className="w-12 h-12 text-primary" />
        </div>
        <h1 className="text-2xl font-bold text-white mb-3">Rate Your Experience</h1>
        {ticketTitle && (
          <p className="text-white/50 text-sm mb-2">
            Ticket: {ticketTitle}
          </p>
        )}
        <p className="text-white/70 mb-8">
          {customerName ? `Hi ${customerName}, h` : 'H'}ow satisfied were you with our support?
        </p>
        
        <div className="flex justify-center mb-6">
          <StarRating 
            rating={rating} 
            onRate={handleRateClick} 
            interactive={!submitting} 
            size="xl" 
          />
        </div>
        
        {rating > 0 && (
          <>
            <p className="text-white/70 text-lg mb-6">
              {ratingLabels[rating]}
            </p>
            <button
              onClick={handleConfirmRating}
              disabled={submitting}
              className="w-full py-3 rounded-xl bg-primary hover:bg-primary/90 text-white font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              data-testid="csat-confirm-rating"
            >
              {submitting ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  Submitting...
                </>
              ) : (
                <>
                  <CheckCircle2 size={18} />
                  Confirm {rating}-Star Rating
                </>
              )}
            </button>
          </>
        )}
        
        {rating === 0 && (
          <p className="text-white/40 text-sm">
            Select a star rating above
          </p>
        )}
      </div>
    </div>
  );
};

export default CSATPage;
