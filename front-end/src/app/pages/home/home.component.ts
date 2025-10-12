import { Component } from '@angular/core';
import { CommunicationService } from 'src/app/services/communication-service/communication.service';
import { Ordonnance, SelectedValue } from 'src/app/interfaces/model';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-home',
  standalone: false,
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.css']
})
export class HomeComponent {
  selectedImage: string | null = null;
  selectedFile: string | null = null;
  selectedFileType: string | null = null;
  sendImageOrFileSubscription: Subscription | any;
  selectedAmFinessNumber: string | null = null;
  ordonnanceData: Ordonnance | null = null;
  
  selectedAmFinessValue: SelectedValue = { value: '', type: 'extracted' };
  selectedPrescriberValue: SelectedValue = { value: '', type: 'extracted' };
  selectedRppsValue: SelectedValue = { value: '', type: 'extracted' };

  constructor(private communicationService: CommunicationService) {}
  
  get isAmFinessNumberList(): boolean {
    return Array.isArray(this.ordonnanceData?.am_finess_number?.value);
  }

  compareSelectedValues(val1: SelectedValue, val2: SelectedValue): boolean {
    return val1 && val2 && val1.value === val2.value && val1.type === val2.type;
  }

  onFileSelected(event: any): void {
    const file = event.target.files[0];  
    if (file && (file.type === 'image/png' || file.type === 'image/jpeg' || file.type === 'application/pdf')) {
      const reader = new FileReader();
      reader.onload = (e: any) => {
        if (file.type.startsWith('image/')) {
          this.selectedImage = e.target.result;
          this.selectedFile = null;
        } else if (file.type === 'application/pdf') {
          this.selectedFile = e.target.result;
          this.selectedImage = null;
          this.selectedFileType = 'pdf';
        }
      };
      reader.readAsDataURL(file);
    } else {
      alert('Please select a PNG, JPEG, or PDF file.');
    }
  }

  onSubmit(): void {
    if (this.selectedImage != null || this.selectedFile != null) {
      this.sendImageOrFileSubscription = this.communicationService
        .sendImage(this.selectedImage)
        .subscribe((response: any) => {
          if (response) {
            const amFinessNumbers = Array.isArray(response.am_finess_number?.value)
              ? response.am_finess_number?.value
              : [response.am_finess_number?.value || ''];

            this.selectedAmFinessNumber = amFinessNumbers.length > 0 ? amFinessNumbers[0] : null;

            this.ordonnanceData = {
              ...response,
              am_finess_number: {
                value: amFinessNumbers,
                confidence: response.am_finess_number?.confidence || 0,
              },
              best_am_finess_number: {
                value: response.best_am_finess_number?.value || '',
              },
              prescriber_name: {
                value: response.prescriber_name?.value || '',
                confidence: response.prescriber_name?.confidence || 0,
              },
              best_prescriber_name: {
                value: response.best_prescriber_name?.value || '',
              },
              rpps_number: {
                value: response.rpps_number?.value || '',
                confidence: response.rpps_number?.confidence || 0,
              },
              best_rpps_number: {
                value: response.best_rpps_number?.value || '',
              },
            };

            // Initialize selected values
            this.selectedAmFinessValue = {
              value: response.am_finess_number?.value || '',
              type: 'extracted'
            };
            this.selectedPrescriberValue = {
              value: response.prescriber_name?.value || '',
              type: 'extracted'
            };
            this.selectedRppsValue = {
              value: response.rpps_number?.value || '',
              type: 'extracted'
            };
          }
        });
    } else {
      alert('Please select an image or PDF');
    }
  }

  ngOnDestroy(): void {
    if (this.sendImageOrFileSubscription) {
      this.sendImageOrFileSubscription.unsubscribe();
    }
  }
}