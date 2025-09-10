import React from 'react';

interface NewPageMessageProps {
  itemType: string;
  className?: string;
  timelineAdjustment?: boolean;
}

const NewPageMessage: React.FC<NewPageMessageProps> = ({
  itemType,
  className = '',
  timelineAdjustment = false,
}) => {
  return (
    <div className={`new-page-message ${className}`}>
      <div className="arrow-container">
        <div className="arrow-up-left">↖</div>
      </div>
      <div className="message-content">
        <h2>
          Load a{itemType[0] === 'a' ? 'n' : ''} {itemType}{' '}
          {!timelineAdjustment && 'or create a new one'}
        </h2>
        <p>
          Select an existing {itemType} from the browser on the upper left
          {timelineAdjustment ? '.' : ', or click "New" to create a new one.'}
          {timelineAdjustment && (
            <>
              <br />
              (To create a new script, go to Text Workflows tab)
            </>
          )}
        </p>
      </div>
    </div>
  );
};

export default NewPageMessage;
