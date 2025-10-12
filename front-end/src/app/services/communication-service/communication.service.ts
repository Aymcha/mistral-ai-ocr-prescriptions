import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { environment } from 'src/environments/environment';

@Injectable({
  providedIn: 'root'
})
export class CommunicationService {
  private readonly baseUrl: string = environment.serverURL;

  constructor(private readonly http: HttpClient) { }

  sendImage(image: any): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/sendImage`, image).pipe(
      catchError(this.handleError<any>('sendImage'))
    );
  }

  handleError<T>(request: string, result?: T): (error: Error) => Observable<T> {
    /***
     * Handle Http operation that failed.
     * @param request: name of the request
     * @param result: optional value to return as the observable result
     * @return Observable<T>
     */
    return () => of(result as T);
  }
}
