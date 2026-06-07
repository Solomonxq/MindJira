class JiraClientError(Exception):
    pass
 
 
class JiraNotFoundError(JiraClientError):
    pass
 
 
class JiraAuthError(JiraClientError):
    pass
 
 
class JiraRateLimitError(JiraClientError):
    pass
 
 
class JiraServerError(JiraClientError):
    pass
 
